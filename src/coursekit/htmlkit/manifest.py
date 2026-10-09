"""imsmanifest.xml of a one-SCO package, SCORM 1.2 or SCORM 2004 (4th edition)."""

from __future__ import annotations

from xml.sax.saxutils import escape, quoteattr

SCORM12 = (
    'xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2" xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xsi:schemaLocation="http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd '
    "http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd "
    'http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd"'
)
SCORM2004 = (
    'xmlns="http://www.imsglobal.org/xsd/imscp_v1p1" xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_v1p3" '
    'xmlns:adlseq="http://www.adlnet.org/xsd/adlseq_v1p3" xmlns:adlnav="http://www.adlnet.org/xsd/adlnav_v1p3" '
    'xmlns:imsss="http://www.imsglobal.org/xsd/imsss" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xsi:schemaLocation="http://www.imsglobal.org/xsd/imscp_v1p1 imscp_v1p1.xsd '
    "http://www.adlnet.org/xsd/adlcp_v1p3 adlcp_v1p3.xsd http://www.adlnet.org/xsd/adlseq_v1p3 adlseq_v1p3.xsd "
    "http://www.adlnet.org/xsd/adlnav_v1p3 adlnav_v1p3.xsd "
    'http://www.imsglobal.org/xsd/imsss imsss_v1p0.xsd"'
)


def build(identifier: str, title: str, files: list[str], standard: str) -> str:
    """`standard` is `scorm_1_2` or `scorm_2004`; `files` are the paths (relative, with `/`) of everything but the manifest."""
    is_2004 = standard == "scorm_2004"
    namespaces = SCORM2004 if is_2004 else SCORM12
    version = "2004 4th Edition" if is_2004 else "1.2"
    scorm_type = "adlcp:scormType" if is_2004 else "adlcp:scormtype"
    listing = "\n".join(f"      <file href={quoteattr(path)}/>" for path in sorted(files))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier={quoteattr(identifier)} version="1.0" {namespaces}>
  <metadata>
    <schema>ADL SCORM</schema>
    <schemaversion>{version}</schemaversion>
  </metadata>
  <organizations default="org-1">
    <organization identifier="org-1">
      <title>{escape(title)}</title>
      <item identifier="item-1" identifierref="res-1">
        <title>{escape(title)}</title>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="res-1" type="webcontent" {scorm_type}="sco" href="index.html">
{listing}
    </resource>
  </resources>
</manifest>
"""
