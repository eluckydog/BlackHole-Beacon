"""BINARY VOTable parser for Simbad TAP responses."""
import struct, base64, xml.etree.ElementTree as ET

def parse_votable(text):
    """Parse Simbad VOTable (handles both TABLEDATA and BINARY)."""
    try:
        root = ET.fromstring(text)
    except:
        return []

    # Check for errors
    for info in root.iter():
        t = info.tag.split("}")[-1]
        if t == "INFO":
            val = info.get("value", "")
            if "ERROR" in val.upper():
                return []

    fields = []
    ns = ""
    for resource in root.iter():
        rt = resource.tag.split("}")[-1]
        if rt != "RESOURCE" or resource.get("type") != "results":
            continue
        table = None
        for c in resource:
            ct = c.tag.split("}")[-1]
            if ct == "TABLE":
                table = c
                ns = c.tag.split("}")[0] if "}" in c.tag else ""
                break
        if table is None:
            return []

        # Extract FIELD definitions
        for c in table:
            ct = c.tag.split("}")[-1]
            if ct == "FIELD":
                fields.append({
                    "name": c.get("name", ""),
                    "datatype": c.get("datatype", "char"),
                    "arraysize": c.get("arraysize", "*"),
                })

        # Find DATA section
        data_el = None
        for c in table:
            ct = c.tag.split("}")[-1]
            if ct == "DATA":
                data_el = c
                break
        if data_el is None:
            return []

        # TABLEDATA or BINARY
        td = None
        bin_el = None
        for c in data_el:
            ct = c.tag.split("}")[-1]
            if ct == "TABLEDATA":
                td = c
            elif ct == "BINARY":
                bin_el = c

        if td is not None:
            # Parse TABLEDATA
            rows = []
            for tr in td:
                tt = tr.tag.split("}")[-1]
                if tt != "TR":
                    continue
                vals = [td.text or "" for td in tr if td.tag.split("}")[-1] == "TD"]
                if vals:
                    rows.append(dict(zip([f["name"] for f in fields], vals)))
            return rows

        if bin_el is not None:
            # Parse BINARY
            stream_el = None
            for c in bin_el:
                ct = c.tag.split("}")[-1]
                if ct == "STREAM":
                    stream_el = c
                    break
            if stream_el is None or not stream_el.text:
                return []

            raw = base64.b64decode(stream_el.text.strip())
            return _parse_binary_rows(raw, fields)

        return []

def _parse_binary_rows(raw, fields):
    """Decode binary VOTable data from Simbad."""
    rows = []
    offset = 0
    row_count = 0
    max_rows = 1000  # safety limit

    while offset < len(raw) and row_count < max_rows:
        row = {}
        for f in fields:
            if offset >= len(raw):
                break
            name = f["name"]
            dtype = f["datatype"]
            asize = f["arraysize"]

            if dtype == "char":
                # Variable-length string: 4-byte int length + data
                if offset + 4 > len(raw):
                    break
                strlen = struct.unpack(">I", raw[offset:offset+4])[0]
                offset += 4
                if strlen > 0 and offset + strlen <= len(raw):
                    row[name] = raw[offset:offset+strlen].decode("utf-8", errors="replace")
                    offset += strlen
                else:
                    row[name] = ""
                    if strlen > 0:
                        offset = min(offset, len(raw))
            elif dtype == "double":
                if offset + 8 <= len(raw):
                    val = struct.unpack(">d", raw[offset:offset+8])[0]
                    row[name] = val
                    offset += 8
                else:
                    break
            elif dtype == "float":
                if offset + 4 <= len(raw):
                    val = struct.unpack(">f", raw[offset:offset+4])[0]
                    row[name] = val
                    offset += 4
                else:
                    break
            elif dtype == "int" or dtype == "long":
                size = 8 if dtype == "long" else 4
                if offset + size <= len(raw):
                    fmt = ">q" if dtype == "long" else ">i"
                    row[name] = struct.unpack(fmt, raw[offset:offset+size])[0]
                    offset += size
                else:
                    break
            elif dtype == "short":
                if offset + 2 <= len(raw):
                    row[name] = struct.unpack(">h", raw[offset:offset+2])[0]
                    offset += 2
                else:
                    break
            elif dtype == "boolean":
                if offset + 1 <= len(raw):
                    row[name] = raw[offset] != 0
                    offset += 1
                else:
                    break
            else:
                # Unknown type - skip 8 bytes as guess
                offset += 8

        if row:
            rows.append(row)
            row_count += 1

    return rows

# Test
if __name__ == "__main__":
    import urllib.request, urllib.parse, ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    TAP = "https://simbad.u-strasbg.fr/simbad/sim-tap/sync"

    ra, dec = 5.959792, -72.075417
    rad = 5.0/3600.0
    sql = ("SELECT main_id, ra, dec, otype, otype_txt, "
           "pmra, pmdec, plx_value, plx_err, sp_type "
           "FROM basic "
           "WHERE CONTAINS(POINT('ICRS', ra, dec), "
           "CIRCLE('ICRS', " + str(ra) + ", " + str(dec) + ", " + str(rad) + "))=1")

    params = {"request":"doQuery","lang":"ADQL","format":"VOTABLE","query":sql}
    url = TAP + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent":"BHBeacon/1.0"})
    resp = urllib.request.urlopen(req, timeout=25, context=ctx)
    text = resp.read().decode("utf-8")

    rows = parse_votable(text)
    print("Rows found:", len(rows))
    for r in rows:
        print("  main_id:", r.get("main_id"))
        print("  otype:", r.get("otype"), "/", r.get("otype_txt"))
        print("  ra:", r.get("ra"), "dec:", r.get("dec"))
        print("  pmra:", r.get("pmra"), "pmdec:", r.get("pmdec"))
        print("  plx:", r.get("plx_value"))
        print("  sp_type:", r.get("sp_type"))
