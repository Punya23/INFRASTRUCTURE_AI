"""Tests for the PIB press-release fetch/parse and rule-based event extraction.

Titles and sentences are copied from real MoRTH releases on PIB (2026). The foundation-stone,
inauguration and DPR cases use constructed text, because the current MoRTH listing has no English
release of those kinds worth quoting — they only prove the rule wiring, not extraction quality.
"""

import json
import re
from datetime import date

import pandas as pd
import pytest
import yaml

from fields.national_highways import events, ingest_pib
from pipeline.shared_layers import ROOT

CFG = yaml.safe_load((ROOT / "config" / "fields" / "national_highways.yaml").read_text())["events"]
RULES = [(re.compile(r["title"], re.IGNORECASE), r) for r in CFG["rules"]]

CABINET_TITLE = ("Cabinet approves construction of 4 Lanning of Badnawar-Petlawad-Thandla-Timarwani section of "
                 "(NH-752D) of Delhi Mumbai expressway in Madhya Pradesh on Hybrid Annuity Mode worth Rs.3,839.42 crore")
CABINET_P1 = ("The Cabinet Committee on Economic Affairs, chaired by the Prime Minister Shri Narendra Modi, today has "
              "approved the development of a 4-lane corridor from Badnawar-Petlawad-Thandla-Timarwani section of "
              "NH-752D having a length of 80.45 kilometer with a total capital cost of Rs.3,839.42 crore.")
CABINET_P2 = "The approved corridor will provide connectivity of Ujjain to Timrawani interchange at Delhi Mumbai Expressway (DME)."
BIDS_TITLE = "NHAI Receives Nine Bids for Six-Laning of Jaipur–Kishangarh Section of NH-48 in Rajasthan"
BIDS_P1 = ("In a step towards strengthening National Highway infrastructure in the state of Rajasthan, NHAI has "
           "received nine bids from the National Highway developers for the project involving upgradation to six "
           "lanes of around 90 km long Jaipur–Kishangarh section of NH-48 in Rajasthan.")
TOLL_TITLE = "NHAI Successfully Launches India’s first Multi-Lane Free Flow Tolling System in Gujarat"
HINDI_TITLE = "दिल्ली-देहरादून इकोनॉमिक कॉरिडोर का उद्घाटन: आधुनिक कनेक्टिविटी और विकास को मिली नई रफ्तार"


def page(title, paragraphs, posted="10 MAR 2026 4:25PM by PIB Delhi"):
    body = "".join(f"<p>{p}</p>" for p in paragraphs)
    return (f'<html><body><div class="innner-page-main-about-us-content-right-part">'
            f'<div id="MinistryName">Ministry of Road Transport &amp; Highways</div><h2>{title}</h2>'
            f'<div id="PrDateTime">Posted On: {posted}</div><div class="WordSection1">{body}</div>'
            f"</div></body></html>").encode()


def listed(prid="2237570", published="2026-03-10", title=CABINET_TITLE):
    return {"prid": prid, "published": published, "title": title, "link": f"https://pib.gov.in/x?PRID={prid}"}


@pytest.mark.parametrize("text, refs", [
    (CABINET_TITLE, ["NH752D"]),
    (("widening of the existing Armoor-Jagtial-Mancherial Section of National Highway (NH)-63 on Hybrid Annuity "
      "Model (HAM) and Jagtial-Karimnagar Section of National Highway (NH)-563 on BOT"), ["NH63", "NH563"]),
    ("construction of 4-Lane Access-Controlled National Highway-927 from Barabanki to Bahraich", ["NH927"]),
    ("Road Tunnel For NH-148AE connecting Dwarka Expressway (NH 248 BB) with Nelson Mandela Marg", ["NH148AE", "NH248BB"]),
    ("Upgradation of the Khagaria-Purnea Section of NH-31 and NH-231 to the 4-Lane Standard", ["NH31", "NH231"]),
    ("Four-Laning of Dhamasiya–Bitada/ Movi and Nasarpore–Malotha Sections of NH-56 in Gujarat", ["NH56"]),
    ("NHAI has issued a Letter of Award for the Capital Region Ring Road Project", []),
])
def test_extract_nh_refs(text, refs):
    assert events.extract_nh_refs(text) == refs


@pytest.mark.parametrize("text, states", [
    (CABINET_TITLE, ["Madhya Pradesh"]),  # 'Delhi Mumbai expressway' is a corridor name, not Delhi
    ("Hybrid Annuity Mode in Uttar Pradesh and Haryana", ["Uttar Pradesh", "Haryana"]),
    ("Connectivity Initiatives Across Jammu & Kashmir and Ladakh", ["Jammu and Kashmir", "Ladakh"]),
    ("Vasant Kunj in Delhi with a Total Project Length of 8.1 Km", ["Delhi"]),
    ("in the state of Rajasthan, NHAI has received", ["Rajasthan"]),
    ("Delhi–Meerut Expressway and the Delhi-Dehradun Economic Corridor", []),
    ("NHAI Awards Contract for Construction of Bhubaneswar Capital Region Ring Road Project", []),
])
def test_extract_states(text, states):
    assert events.extract_states(text) == states


@pytest.mark.parametrize("text, cost", [
    ("worth Rs. 6969.67 crore on Hybrid Annuity Mode", 6969.67),
    ("Union Minister has approved ₹1,427.61 crore for the construction", 1427.61),
    ("awarded to M/s Maruti Infracreation Pvt. Ltd. at a cost of Rs.130.65 Crores under", 130.65),
    ("Rs.3,839.42 crore ... capital cost of Rs.3,839.42 crore", 3839.42),   # the same figure twice is one figure
    ("Rs.3630.77 crore and Rs.3000 crore", None),                            # two figures: ambiguous, not averaged
    ("a total capital cost to be decided", None),
])
def test_extract_cost_crore(text, cost):
    assert events.extract_cost_crore(text) == cost


@pytest.mark.parametrize("text, km", [
    ("4-Lane Standard (143. 529 kms) at a cost", 143.529),   # PIB's own stray space after the decimal point
    ("a length of 80.45 kilometer with", 80.45),
    ("Total Project Length of 8.1 Km worth", 8.1),
    ("(125.01 kms) of Hiwarkhedi ... of length (108. 643 kms)", None),
    ("from Km 142.880 to Km 170.880 of NH-544", None),       # chainage, not a length
    ("Part of Coastal Highway having total length of 163.180 Km ... combined total length of 160.18 km", None),
])
def test_extract_length_km(text, km):
    assert events.extract_length_km(text) == km


def test_extract_modes():
    assert events.extract_modes("Hybrid Annuity Model (HAM) ... Build-Operate-Transfer (Toll) [BOT (Toll)]") == ["HAM", "BOT"]
    assert events.extract_modes("Engineering, Procurement and Construction (EPC) mode") == ["EPC"]
    assert events.extract_modes("BOT (Toll) Mode") == ["BOT"]
    assert events.extract_modes("no mode stated") == []


def test_evidence_sentence():
    approved = re.compile(r"\bapproved\b", re.IGNORECASE)
    got = events.evidence_sentence([CABINET_P1, CABINET_P2], approved, 450, 4)
    assert got == CABINET_P1 and "Rs.3,839.42 crore" in got  # the full stop inside 'Rs.3,839.42' does not split
    # a match beyond the opening paragraphs is ignored
    assert events.evidence_sentence(["a", "b", "c", "d", "The Cabinet approved it."], approved, 450, 4) is None
    # a long sentence is cut to a verbatim prefix; a cut that loses the match returns None
    long_sentence = "x " * 100 + "approved the road"
    assert events.evidence_sentence([long_sentence], approved, 60, 4) is None
    cut = events.evidence_sentence(["approved " + "y " * 100], approved, 60, 4)
    assert cut is not None and len(cut) <= 60 and ("approved " + "y " * 100).startswith(cut)


def test_parse_release():
    rel = ingest_pib.parse_release(page(CABINET_TITLE, [CABINET_P1, CABINET_P2]))
    assert rel["title"] == CABINET_TITLE
    assert rel["posted_on"] == date(2026, 3, 10)
    assert rel["paragraphs"] == [CABINET_P1, CABINET_P2]
    assert rel["language"] == "en"
    hindi = ingest_pib.parse_release(page(HINDI_TITLE, ["नमस्ते"], "प्रविष्टि तिथि: 14 APR 2026 4:31PM by PIB Delhi"))
    assert hindi["language"] == "other" and hindi["posted_on"] == date(2026, 4, 14)


@pytest.mark.parametrize("raw", [
    b"<html><body>The Page you have requested does not exist</body></html>",   # PIB's soft-404 answers 200
    page(CABINET_TITLE, [CABINET_P1], posted="sometime in March"),
    page(CABINET_TITLE, []),
])
def test_parse_release_rejects_pages_without_a_release(raw):
    with pytest.raises(ValueError):
        ingest_pib.parse_release(raw)


def test_listing_rows_keeps_every_entry():
    def entry(title, link, published="2026-03-10", file=None):
        return {"title": title, "link": link, "published_date": published, "file": file}
    listing = {"page": {"files": [
        {"name": "March", "files_data": [
            entry("A", "https://pib.gov.in/PressReleasePage.aspx?PRID=1&reg=3&lang=1"),
            entry("B", "https://pib.gov.in/PressReleasePage.aspx?PRID=2"),
            entry("no link", None, file="documents/x.pdf"),
        ]},
        {"name": "Other", "files_data": [
            entry("A again", "https://pib.gov.in/PressReleasePage.aspx?PRID=1"),   # same PRID in two groups
            entry("PIB home", "http://pib.gov.in/indexd.aspx"),
            entry("PIB home", "http://pib.gov.in/indexd.aspx"),                    # exact duplicate
        ]},
        {"name": "empty"},
    ]}}
    rows = ingest_pib.listing_rows(listing)
    assert rows["prid"].tolist() == ["1", "2", None, None]
    assert rows["title"].tolist() == ["A", "B", "no link", "PIB home"]


@pytest.fixture
def pib_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(events, "RAW_PIB", tmp_path)
    return tmp_path


def classify(prid="2237570", **kw):
    return events.classify_release(listed(prid, **kw), {prid: "2026-09-30T00:00:00Z"}, RULES, CFG)


def test_classify_cabinet_approval(pib_dir):
    (pib_dir / "2237570.html").write_bytes(page(CABINET_TITLE, [CABINET_P1, CABINET_P2]))
    classification, event, reasons = classify()
    assert (classification, reasons) == ("event", [])
    assert event["event_type"] == "cabinet_approval" and event["stage"] == "approved"
    assert event["event_date"] == "2026-03-10"
    assert event["nh_refs"] == ["NH752D"] and event["states"] == ["Madhya Pradesh"]
    assert event["cost_crore"] == 3839.42 and event["length_km"] == 80.45 and event["modes"] == ["HAM"]
    assert event["evidence"] == CABINET_P1
    assert event["confidence"] == 0.9   # base 0.75 + NH ref, state and cost anchors at 0.05 each
    assert event["id"] == "nh_project_event:pib_morth:2237570"
    assert event["source_url"] == "https://pib.gov.in/PressReleasePage.aspx?PRID=2237570"
    assert event["extractor"] == events.EXTRACTOR and event["fetched_at"] == "2026-09-30T00:00:00Z"


def test_classify_bids_received(pib_dir):
    (pib_dir / "2240918.html").write_bytes(page(BIDS_TITLE, [BIDS_P1], "16 MAR 2026 6:01PM by PIB Delhi"))
    classification, event, reasons = classify("2240918", published="2026-03-16", title=BIDS_TITLE)
    assert (classification, reasons) == ("event", [])
    assert (event["event_type"], event["stage"]) == ("bids_received", "tendered")
    assert event["nh_refs"] == ["NH48"] and event["states"] == ["Rajasthan"] and event["length_km"] == 90.0
    assert event["cost_crore"] is None and event["confidence"] == 0.85


@pytest.mark.parametrize("title, paragraph, kind, stage", [
    ("Minister Lays Foundation Stone of 4-lane Example Bypass on NH-99 in Karnataka",
     "The Minister today laid the foundation stone of the 4-lane Example Bypass on NH-99 in Karnataka.",
     "foundation_stone", "under_construction"),
    ("Prime Minister inaugurates 6-lane Example Expressway on NH-77 in Bihar",
     "The Prime Minister today inaugurated the 6-lane Example Expressway on NH-77 in Bihar.",
     "inaugurated", "operational"),
    ("NHAI Undertakes DPR Preparation to Decongest Example Loop on NH-19 in Delhi",
     "NHAI has initiated preparation of the DPR to decongest the Example Loop on NH-19 in Delhi.",
     "dpr_preparation", "proposed"),
])
def test_classify_other_stage_rules(pib_dir, title, paragraph, kind, stage):
    (pib_dir / "1.html").write_bytes(page(title, [paragraph]))
    classification, event, reasons = classify("1", title=title)
    assert (classification, reasons) == ("event", [])
    assert (event["event_type"], event["stage"]) == (kind, stage)


def test_classify_every_release_gets_a_reason(pib_dir):
    (pib_dir / "1.html").write_bytes(page(TOLL_TITLE, ["NHAI has launched MLFF tolling."]))
    assert classify("1", title=TOLL_TITLE) == ("no_project_event", None, [])
    (pib_dir / "2.html").write_bytes(page(HINDI_TITLE, ["नमस्ते"]))
    assert classify("2", title=HINDI_TITLE)[::2] == ("unsupported_language", ["language_other"])
    assert classify("3")[::2] == ("not_fetched", ["page_not_on_disk"])
    (pib_dir / "4.html").write_bytes(b"<html>soft 404</html>")
    assert classify("4")[0] == "unparsed"
    no_link = {"prid": None, "published": "2026-09-23", "title": "Minister Lays Foundation Stones", "link": None}
    assert events.classify_release(no_link, {}, RULES, CFG)[::2] == ("no_release_text", ["no_pib_release_link"])


def test_classify_sends_failed_verification_to_review(pib_dir):
    (pib_dir / "2237570.html").write_bytes(page(CABINET_TITLE, [CABINET_P1, CABINET_P2]))
    # the MoRTH listing disagrees with the PIB page on the date and the title
    _, event, reasons = classify(published="2026-03-20", title="Cabinet approves something else")
    assert event is not None and reasons == ["listing_date_mismatch", "listing_title_mismatch"]
    # a release that states the stage but names no road, state or cost cannot be placed anywhere
    (pib_dir / "5.html").write_bytes(page("Cabinet approves a new scheme", ["The Cabinet today approved the scheme."]))
    _, event, reasons = classify("5", title="Cabinet approves a new scheme")
    assert reasons == ["no_anchor"]
    # the title matches but no opening sentence states the stage
    (pib_dir / "6.html").write_bytes(page("Cabinet approves NH-9 widening in Bihar", ["Details will follow."]))
    assert classify("6", title="Cabinet approves NH-9 widening in Bihar")[::2] == ("review", ["no_evidence_sentence"])


def test_verify_event_catches_a_quote_that_is_not_in_the_release():
    release = {"paragraphs": [CABINET_P1], "posted_on": date(2026, 3, 10), "title": CABINET_TITLE}
    rule = next(r for _, r in RULES if r["type"] == "cabinet_approval")
    event, _ = events.extract_event(release, rule, CFG)
    assert events.verify_event(event, release, listed(), CFG) == []
    event["evidence"] = event["evidence"].replace("80.45", "90.45")
    assert events.verify_event(event, release, listed(), CFG) == ["quote_not_in_source"]


def test_build_events_says_what_to_run_when_the_press_step_has_not(tmp_path, monkeypatch):
    (tmp_path / "config" / "fields").mkdir(parents=True)
    (tmp_path / "config" / "fields" / "national_highways.yaml").write_text(
        (ROOT / "config" / "fields" / "national_highways.yaml").read_text())
    monkeypatch.setattr(events, "ROOT", tmp_path)
    with pytest.raises(FileNotFoundError, match="fields.national_highways press"):
        events.build_events()


def test_build_events_writes_outputs_and_is_idempotent(pib_dir, tmp_path, monkeypatch):
    out = tmp_path / "out"
    listing_file = tmp_path / "listing.json"
    listing_file.write_text(json.dumps({"page": {"files": [{"name": "March", "files_data": [
        {"title": CABINET_TITLE, "link": "https://pib.gov.in/PressReleasePage.aspx?PRID=2237570",
         "published_date": "2026-03-10", "file": None},
        {"title": "PIB home", "link": "http://pib.gov.in/indexd.aspx", "published_date": "2026-03-10", "file": None},
    ]}]}}))
    (pib_dir / "2237570.html").write_bytes(page(CABINET_TITLE, [CABINET_P1, CABINET_P2]))
    (tmp_path / "config" / "fields").mkdir(parents=True)
    (tmp_path / "config" / "fields" / "national_highways.yaml").write_text(
        (ROOT / "config" / "fields" / "national_highways.yaml").read_text())
    (tmp_path / "data" / "manifests").mkdir(parents=True)
    (tmp_path / "data" / "manifests" / "pib_morth_press_releases.yaml").write_text(yaml.safe_dump({
        "license": "test licence",
        "files": [{"file": "data/raw/pib/2237570.html", "fetched_at": "2026-09-30T00:00:00Z"}]}))
    monkeypatch.setattr(events, "OUT", out)
    monkeypatch.setattr(events, "LISTING", listing_file)
    monkeypatch.setattr(events, "ROOT", tmp_path)

    verified = events.build_events()
    assert verified["source_ref"].tolist() == ["2237570"] and verified.loc[0, "license"] == "test licence"
    press = pd.read_csv(out / "press_releases.csv")
    assert press["classification"].tolist() == ["event", "no_release_text"]   # nothing is dropped
    assert pd.read_csv(out / "nh_events_review.csv").empty
    events.build_events()   # a second run gives the same rows
    assert pd.read_parquet(out / "nh_events.parquet")["id"].tolist() == ["nh_project_event:pib_morth:2237570"]
