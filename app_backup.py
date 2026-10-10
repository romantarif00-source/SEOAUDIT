
import ipaddress
import socket
from urllib.parse import urljoin, urlparse, urldefrag

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup


st.set_page_config(
    page_title="SEO Analyzer",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 SEO Analyzer")
st.write(
    "Analyze on-page and basic technical SEO for a public webpage. "
    "The score is based on the checks performed by this tool."
)

MAX_LINKS_TO_CHECK = 15
REQUEST_TIMEOUT = 8
USER_AGENT = "Mozilla/5.0 (compatible; BasicSEOAnalyzer/1.0)"


def normalize_url(raw_url):
    raw_url = raw_url.strip()

    if not raw_url:
        raise ValueError("Please enter a website URL.")

    if not raw_url.startswith(("https://", "http://")):
        raw_url = "https://" + raw_url

    parsed = urlparse(raw_url)

    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Please enter a valid HTTP or HTTPS URL.")

    return raw_url


def is_public_host(hostname):
    """Avoid requesting localhost and private network addresses."""
    try:
        addresses = socket.getaddrinfo(
            hostname, None, type=socket.SOCK_STREAM
        )

        if not addresses:
            return False

        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])

            if not ip.is_global:
                return False

        return True

    except (socket.gaierror, ValueError, OSError):
        return False


def add_check(rows, name, status, result, recommendation, weight):
    rows.append({
        "SEO Check": name,
        "Status": status,
        "Result": result,
        "Recommendation": recommendation,
        "Weight": weight
    })


def check_internal_links(session, links, page_url):
    """Check a limited number of same-domain links."""
    page_host = (urlparse(page_url).hostname or "").lower()
    candidates = []

    for link in links:
        href = link.get("href", "").strip()

        if not href:
            continue

        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        absolute_url = urldefrag(urljoin(page_url, href))[0]
        parsed = urlparse(absolute_url)

        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            continue

        if parsed.hostname.lower() == page_host:
            if absolute_url not in candidates:
                candidates.append(absolute_url)

    candidates = candidates[:MAX_LINKS_TO_CHECK]

    if not candidates:
        return (
            "NOT CHECKED",
            "No internal links found to test",
            "Add relevant internal links where they help visitors navigate."
        )

    broken = []
    could_not_check = []

    for link_url in candidates:
        try:
            response = session.get(
                link_url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
                stream=True
            )
            status_code = response.status_code
            response.close()

            if status_code >= 400:
                broken.append(f"{link_url} (HTTP {status_code})")

        except requests.RequestException:
            could_not_check.append(link_url)

    if broken:
        sample = "; ".join(broken[:5])
        return (
            "FAIL",
            f"{len(broken)} broken/error link(s) out of "
            f"{len(candidates)} checked. {sample}",
            "Fix incorrect URLs and links returning HTTP 4xx/5xx errors."
        )

    if could_not_check:
        return (
            "NEEDS IMPROVEMENT",
            f"{len(could_not_check)} link(s) could not be verified; "
            f"{len(candidates)} attempted",
            "Manually test links that timed out or blocked automated requests."
        )

    return (
        "PASS",
        f"All {len(candidates)} checked internal links responded below HTTP 400",
        "Continue checking internal links regularly."
    )


def analyze_website(website):
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    try:
        parsed_input = urlparse(website)

        if not is_public_host(parsed_input.hostname):
            raise ValueError(
                "This tool only checks publicly reachable website hosts. "
                "Localhost and private network addresses are not allowed."
            )

        response = session.get(
            website,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        final_url = response.url
        final_parsed = urlparse(final_url)

        if not is_public_host(final_parsed.hostname):
            raise ValueError(
                "The website redirected to a non-public host. "
                "For safety, the analysis was stopped."
            )

        soup = BeautifulSoup(response.text, "html.parser")
        rows = []

        # 1. HTTP response
        if response.status_code == 200:
            add_check(
                rows, "HTTP Status", "PASS",
                f"HTTP {response.status_code}",
                "The page returned HTTP 200.", 15
            )
        else:
            add_check(
                rows, "HTTP Status", "FAIL",
                f"HTTP {response.status_code}",
                "Investigate the response code. The page should normally "
                "return HTTP 200 when it is accessible and working.", 15
            )

        # 2. HTTPS
        if final_parsed.scheme == "https":
            add_check(
                rows, "HTTPS", "PASS", "HTTPS is enabled",
                "The final page URL uses HTTPS.", 10
            )
        else:
            add_check(
                rows, "HTTPS", "FAIL", "Page uses HTTP",
                "Configure HTTPS and redirect visitors to the secure URL.", 10
            )

        # 3. Page title
        title_tag = soup.find("title")
        title = title_tag.get_text(" ", strip=True) if title_tag else ""

        if title:
            add_check(
                rows, "Page Title", "PASS", title,
                "A title element is present.", 10
            )
        else:
            add_check(
                rows, "Page Title", "FAIL", "Missing",
                "Add a unique, descriptive title element.", 10
            )

        # 4. Title length: guideline, not a guaranteed ranking factor
        if not title:
            add_check(
                rows, "Title Length", "NOT CHECKED", "No title",
                "Add a title before reviewing its length.", 3
            )
        elif 30 <= len(title) <= 60:
            add_check(
                rows, "Title Length", "PASS", f"{len(title)} characters",
                "The title length is within a common guideline.", 3
            )
        else:
            add_check(
                rows, "Title Length", "NEEDS IMPROVEMENT",
                f"{len(title)} characters",
                "Review whether the title is clear and concise. "
                "30–60 characters is only a guideline.", 3
            )

        # 5. Meta description
        meta_description = soup.find(
            "meta", attrs={"name": lambda value: value and
                           value.lower() == "description"}
        )
        description = (
            meta_description.get("content", "").strip()
            if meta_description else ""
        )

        if description:
            add_check(
                rows, "Meta Description", "PASS", description,
                "A meta description is present.", 8
            )
        else:
            add_check(
                rows, "Meta Description", "FAIL", "Missing",
                "Add a useful description that accurately summarizes "
                "the page.", 8
            )

        # 6. Meta description length
        if not description:
            add_check(
                rows, "Description Length", "NOT CHECKED", "No description",
                "Add a meta description before reviewing its length.", 2
            )
        elif 120 <= len(description) <= 160:
            add_check(
                rows, "Description Length", "PASS",
                f"{len(description)} characters",
                "The length is within a common guideline.", 2
            )
        else:
            add_check(
                rows, "Description Length", "NEEDS IMPROVEMENT",
                f"{len(description)} characters",
                "Review clarity and usefulness. 120–160 characters "
                "is a guideline, not a strict rule.", 2
            )

        # 7. H1 heading
        h1_tags = soup.find_all("h1")
        h1_text = " | ".join(
            heading.get_text(" ", strip=True) for heading in h1_tags
        )

        if len(h1_tags) == 1 and h1_text:
            add_check(
                rows, "Main H1", "PASS", h1_text,
                "One non-empty H1 heading was found.", 8
            )
        elif len(h1_tags) == 0:
            add_check(
                rows, "Main H1", "FAIL", "No H1 found",
                "Add a clear main heading when appropriate for the page.", 8
            )
        else:
            add_check(
                rows, "Main H1", "NEEDS IMPROVEMENT",
                f"{len(h1_tags)} H1 tags",
                "Review whether the page has a clear, meaningful main heading. "
                "Multiple H1s are not automatically a Google penalty.", 8
            )

        # 8. Heading structure
        headings = {
            f"H{i}": len(soup.find_all(f"h{i}"))
            for i in range(1, 7)
        }
        heading_summary = ", ".join(
            f"{key}: {value}" for key, value in headings.items()
        )

        if any(headings[f"H{i}"] for i in range(1, 7)):
            add_check(
                rows, "Heading Structure", "PASS", heading_summary,
                "Review headings for a logical structure and useful content.", 5
            )
        else:
            add_check(
                rows, "Heading Structure", "FAIL", "No heading tags found",
                "Use headings to organize the page content where appropriate.", 5
            )

        # 9. Image ALT text
        images = soup.find_all("img")
        missing_alt = [
            img for img in images
            if not img.has_attr("alt")
        ]

        if not images:
            add_check(
                rows, "Image ALT Text", "NOT CHECKED", "No images found",
                "No image ALT check was applicable to this HTML page.", 7
            )
        elif not missing_alt:
            add_check(
                rows, "Image ALT Text", "PASS",
                f"All {len(images)} images have an ALT attribute",
                "Ensure ALT text is descriptive for meaningful images. "
                "Decorative images can use alt=\"\".", 7
            )
        else:
            add_check(
                rows, "Image ALT Text", "FAIL",
                f"{len(missing_alt)} of {len(images)} images lack ALT",
                "Add appropriate ALT text to meaningful images. "
                "Use alt=\"\" for decorative images.", 7
            )

        # 10. Canonical
        canonical = soup.find(
            "link",
            rel=lambda value: value and
            "canonical" in [part.lower() for part in
                            (value if isinstance(value, list)
                             else value.split())]
        )
        canonical_url = (
            urljoin(final_url, canonical.get("href", "").strip())
            if canonical and canonical.get("href", "").strip()
            else ""
        )

        if canonical_url:
            add_check(
                rows, "Canonical URL", "PASS", canonical_url,
                "Verify that the canonical points to the preferred page URL.", 8
            )
        else:
            add_check(
                rows, "Canonical URL", "NEEDS IMPROVEMENT", "Not found",
                "Review whether this page needs a canonical tag. "
                "It is not required on every page.", 8
            )

        # 11. Mobile viewport
        viewport = soup.find(
            "meta", attrs={"name": lambda value: value and
                           value.lower() == "viewport"}
        )

        if viewport and viewport.get("content", "").strip():
            add_check(
                rows, "Mobile Viewport", "PASS",
                viewport.get("content", "").strip(),
                "The viewport meta tag is present. Actual mobile usability "
                "requires a separate test.", 7
            )
        else:
            add_check(
                rows, "Mobile Viewport", "FAIL", "Not found",
                "Add a suitable viewport meta tag and test the page on mobile.", 7
            )

        # 12. Indexing directives
        robots_meta = soup.find_all(
            "meta", attrs={"name": lambda value: value and
                           value.lower() in ("robots", "googlebot")}
        )
        robots_values = [
            tag.get("content", "").lower()
            for tag in robots_meta
        ]
        x_robots = response.headers.get("X-Robots-Tag", "").lower()
        directives = robots_values + ([x_robots] if x_robots else [])
        noindex_found = any(
            "noindex" in value for value in directives
        )

        if noindex_found:
            add_check(
                rows, "Indexing Directives", "FAIL",
                "; ".join(directives),
                "A noindex directive was detected. Confirm that the page "
                "is intentionally excluded from search results.", 10
            )
        else:
            add_check(
                rows, "Indexing Directives", "PASS",
                "; ".join(directives) if directives
                else "No noindex directive detected",
                "This check does not prove that Google can index the page. "
                "Check robots.txt, status, rendering and Search Console too.", 10
            )

        # 13. Internal links
        links = soup.find_all("a", href=True)
        internal_links = []

        page_host = (final_parsed.hostname or "").lower()

        for link in links:
            absolute = urljoin(final_url, link.get("href", "").strip())
            link_host = (urlparse(absolute).hostname or "").lower()

            if link_host == page_host and urlparse(absolute).scheme in (
                "http", "https"
            ):
                internal_links.append(absolute)

        if internal_links:
            add_check(
                rows, "Internal Links", "PASS",
                f"{len(set(internal_links))} internal link(s) found",
                "Make sure important pages link to each other with useful "
                "anchor text.", 3
            )
        else:
            add_check(
                rows, "Internal Links", "NEEDS IMPROVEMENT", "None found",
                "Add relevant internal links if appropriate for this page.", 3
            )

        # 14. Limited broken-link check
        with st.spinner("Checking a sample of internal links..."):
            link_status, link_result, link_recommendation = (
                check_internal_links(session, links, final_url)
            )

        add_check(
            rows, "Sample Internal Link Test",
            link_status, link_result, link_recommendation, 2
        )

        # Build weighted score. NOT CHECKED rows are excluded.
        report = pd.DataFrame(rows)
        eligible = report[report["Status"] != "NOT CHECKED"].copy()

        weights = eligible["Weight"].sum()

        points = {
            "PASS": 1.0,
            "NEEDS IMPROVEMENT": 0.5,
            "FAIL": 0.0
        }

        earned = sum(
            row["Weight"] * points.get(row["Status"], 0)
            for _, row in eligible.iterrows()
        )

        score = round((earned / weights) * 100) if weights else 0

        return {
            "report": report,
            "score": score,
            "passed": int((report["Status"] == "PASS").sum()),
            "failed": int((report["Status"] == "FAIL").sum()),
            "needs_improvement": int(
                (report["Status"] == "NEEDS IMPROVEMENT").sum()
            ),
            "not_checked": int(
                (report["Status"] == "NOT CHECKED").sum()
            ),
            "final_url": final_url,
            "http_status": response.status_code
        }

    finally:
        session.close()


website = st.text_input(
    "Enter a public webpage URL",
    placeholder="https://example.com"
)

if st.button("Analyze Website", type="primary"):
    try:
        clean_url = normalize_url(website)

        with st.spinner("Analyzing webpage..."):
            result = analyze_website(clean_url)

        st.subheader("SEO Audit Results")
        st.caption(f"Page analyzed: {result['final_url']}")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("SEO Score", f"{result['score']}/100")

        with col2:
            st.metric("Passed", result["passed"])

        with col3:
            st.metric(
                "Failed",
                result["failed"]
            )

        with col4:
            st.metric(
                "Needs Review",
                result["needs_improvement"] + result["not_checked"]
            )

        st.progress(result["score"] / 100)

        if result["score"] >= 85:
            st.success("Strong result for the checks performed.")
        elif result["score"] >= 65:
            st.info("Some SEO improvements may be needed.")
        else:
            st.warning("Several checked items need attention.")

        st.subheader("Detailed SEO Report")
        st.dataframe(
            result["report"].drop(columns=["Weight"]),
            use_container_width=True,
            hide_index=True
        )

        csv_data = result["report"].to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "Download SEO Report (CSV)",
            data=csv_data,
            file_name="seo_detailed_report.csv",
            mime="text/csv"
        )

        st.info(
            "This is a weighted audit of the HTML and HTTP response "
            "visible to this tool. It does not measure all ranking factors, "
            "JavaScript-rendered content, real Core Web Vitals, backlinks, "
            "content quality, or Google indexing status. Only a limited "
            "sample of internal links is tested."
        )

    except ValueError as error:
        st.error(str(error))

    except requests.RequestException as error:
        st.error(
            f"Could not access the webpage: {error}. "
            "The website may block automated requests or be unavailable."
        )

    except Exception as error:
        st.error(f"Unexpected error: {error}")
