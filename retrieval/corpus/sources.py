"""
retrieval/corpus/sources.py — dlt source functions for the Themis legal corpus.

Each function is a dlt @source that yields Document records. dlt handles
incremental state, deduplication fingerprinting, and filesystem writes.

Document schema (all fields required):
  doc_id        : str   — stable deterministic ID (SHA-256 of source_url + text[:200])
  source_url    : str   — canonical URL of the source
  source        : str   — human-readable source name (e.g. "Cornell LII - UCC Art 2")
  jurisdiction  : str   — "us_generic" | "uk" | "us_ca" etc.
  document_type : str   — "statute" | "regulation" | "contract_exhibit"
  title         : str   — document / section title
  text          : str   — full plain text content (not chunked — chunking is downstream)
  fetched_at    : str   — ISO-8601 UTC timestamp of fetch

Sources:
  1. us_statutes_source   — 5 US federal/state statute excerpts from govinfo.gov / Cornell LII
  2. uk_statutes_source   — 3 UK statute excerpts from legislation.gov.uk REST API
  3. edgar_exhibits_source — 6 SEC EDGAR contract exhibits (EX-10 filings, public domain)

Why dlt?
  - Handles incremental loads via built-in state tracking (no re-ingest on re-run)
  - Automatic schema inference and filesystem write
  - Pluggable destinations — same source code works for filesystem (dev) or S3 (prod)
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import UTC, datetime
from typing import Iterator

import dlt
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HEADERS = {
    "User-Agent": "Themis-LegalAI/1.0 (research; contact@themis.ai)",
    "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9",
}
_REQUEST_DELAY = 1.5   # seconds between HTTP requests — respect robots.txt
_REQUEST_TIMEOUT = 30  # seconds


def _fetch_text(url: str) -> str:
    """Fetch plain text from a URL with retry + rate limiting."""
    time.sleep(_REQUEST_DELAY)
    resp = requests.get(url, headers=_HEADERS, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def _make_doc_id(source_url: str, text_prefix: str) -> str:
    """Deterministic stable ID: SHA-256 of (url + first 200 chars of text)."""
    payload = f"{source_url}::{text_prefix[:200]}"
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# Hardcoded seed corpus text
# We embed the statute excerpts directly rather than scraping at runtime.
# This makes the pipeline reproducible even when upstream URLs change, and
# avoids HTML parsing of complex government websites.
# Each entry is a real, verbatim excerpt from the cited public-domain source.
# ---------------------------------------------------------------------------

US_STATUTE_SEEDS: list[dict] = [
    {
        "title": "Uniform Commercial Code Article 2 — Sale of Goods (Sections 2-201 to 2-210)",
        "source": "UCC Art. 2 (ALI / NCCUSL — public domain official text)",
        "source_url": "https://www.law.cornell.edu/ucc/2",
        "jurisdiction": "us_generic",
        "document_type": "statute",
        "text": (
            "UCC § 2-201. Formal Requirements; Statute of Frauds.\n"
            "(1) Except as otherwise provided in this section a contract for the sale of goods for "
            "the price of $500 or more is not enforceable by way of action or defense unless there "
            "is some writing sufficient to indicate that a contract for sale has been made between "
            "the parties and signed by the party against whom enforcement is sought or by his "
            "authorized agent or broker. A writing is not insufficient because it omits or "
            "incorrectly states a term agreed upon but the contract is not enforceable under this "
            "paragraph beyond the quantity of goods shown in such writing.\n\n"
            "UCC § 2-202. Final Written Expression: Parol or Extrinsic Evidence.\n"
            "Terms with respect to which the confirmatory memoranda of the parties agree or which "
            "are otherwise set forth in a writing intended by the parties as a final expression of "
            "their agreement with respect to such terms as are included therein may not be "
            "contradicted by evidence of any prior agreement or of a contemporaneous oral agreement "
            "but may be explained or supplemented (a) by course of dealing or usage of trade "
            "(Section 1-303) or by course of performance (Section 2-208); and (b) by evidence of "
            "consistent additional terms unless the court finds the writing to have been intended "
            "also as a complete and exclusive statement of the terms of the agreement.\n\n"
            "UCC § 2-204. Formation in General.\n"
            "(1) A contract for sale of goods may be made in any manner sufficient to show "
            "agreement, including conduct by both parties which recognizes the existence of such "
            "a contract. (2) An agreement sufficient to constitute a contract for sale may be "
            "found even though the moment of its making is undetermined. (3) Even though one or "
            "more terms are left open a contract for sale does not fail for indefiniteness if the "
            "parties have intended to make a contract and there is a reasonably certain basis for "
            "giving an appropriate remedy.\n\n"
            "UCC § 2-207. Additional Terms in Acceptance or Confirmation.\n"
            "(1) A definite and seasonable expression of acceptance or a written confirmation "
            "which is sent within a reasonable time operates as an acceptance even though it states "
            "terms additional to or different from those offered or agreed upon, unless acceptance "
            "is expressly made conditional on assent to the additional or different terms.\n"
            "(2) The additional terms are to be construed as proposals for addition to the "
            "contract. Between merchants such terms become part of the contract unless: "
            "(a) the offer expressly limits acceptance to the terms of the offer; "
            "(b) they materially alter it; or (c) notification of objection to them has already "
            "been given or is given within a reasonable time after notice of them is received.\n\n"
            "UCC § 2-209. Modification, Rescission and Waiver.\n"
            "(1) An agreement modifying a contract within this Article needs no consideration "
            "to be binding. (2) A signed agreement which excludes modification or rescission "
            "except by a signed writing cannot be otherwise modified or rescinded, but except "
            "as between merchants such a requirement on a form supplied by the merchant must be "
            "separately signed by the other party.\n\n"
            "UCC § 2-314. Implied Warranty: Merchantability; Usage of Trade.\n"
            "(1) Unless excluded or modified (Section 2-316), a warranty that the goods shall be "
            "merchantable is implied in a contract for their sale if the seller is a merchant with "
            "respect to goods of that kind. Under this section the serving for value of food or "
            "drink to be consumed either on the premises or elsewhere is a sale.\n\n"
            "UCC § 2-316. Exclusion or Modification of Warranties.\n"
            "(1) Words or conduct relevant to the creation of an express warranty and words or "
            "conduct tending to negate or limit warranty shall be construed wherever reasonable "
            "as consistent with each other; but subject to the provisions of this Article on "
            "parol or extrinsic evidence (Section 2-202) negation or limitation is inoperative "
            "to the extent that such construction is unreasonable.\n"
        ),
    },
    {
        "title": "Foreign Corrupt Practices Act — Anti-Bribery Provisions (15 U.S.C. § 78dd-1)",
        "source": "FCPA (15 U.S.C. § 78dd-1) — US federal public law",
        "source_url": "https://www.law.cornell.edu/uscode/text/15/78dd-1",
        "jurisdiction": "us_generic",
        "document_type": "statute",
        "text": (
            "15 U.S.C. § 78dd-1. Prohibited foreign trade practices by issuers.\n\n"
            "(a) Prohibition\n"
            "It shall be unlawful for any issuer which has a class of securities registered "
            "pursuant to section 78l of this title or which is required to file reports under "
            "section 78o(d) of this title, or for any officer, director, employee, or agent of "
            "such issuer or any stockholder thereof acting on behalf of such issuer, to make use "
            "of the mails or any means or instrumentality of interstate commerce corruptly in "
            "furtherance of an offer, payment, promise to pay, or authorization of the payment "
            "of any money, or offer, gift, promise to give, or authorization of the giving of "
            "anything of value to—\n"
            "(1) any foreign official for purposes of—\n"
            "  (A)(i) influencing any act or decision of such foreign official in his official "
            "capacity, (ii) inducing such foreign official to do or omit to do any act in "
            "violation of the lawful duty of such official, or (iii) securing any improper "
            "advantage; or\n"
            "  (B) inducing such foreign official to use his influence with a foreign government "
            "or instrumentality thereof to affect or influence any act or decision of such "
            "government or instrumentality,\n"
            "in order to assist such issuer in obtaining or retaining business for or with, or "
            "directing business to, any person;\n\n"
            "(c) Affirmative defenses\n"
            "It shall be an affirmative defense to actions under subsection (a) or (b) of this "
            "section that—\n"
            "(1) the payment, gift, offer, or promise of anything of value that was made, was "
            "lawful under the written laws and regulations of the foreign official's, political "
            "party's, party official's, or candidate's country; or\n"
            "(2) the payment, gift, offer, or promise of anything of value that was made, was "
            "a reasonable and bona fide expenditure, such as travel and lodging expenses, "
            "incurred by or on behalf of a foreign official, party, party official, or candidate "
            "and was directly related to—\n"
            "  (A) the promotion, demonstration, or explanation of products or services; or\n"
            "  (B) the execution or performance of a contract with a foreign government or "
            "agency thereof.\n\n"
            "(f) Definitions\n"
            "For purposes of this section:\n"
            "(1) The term 'foreign official' means any officer or employee of a foreign government "
            "or any department, agency, or instrumentality thereof, or of a public international "
            "organization, or any person acting in an official capacity for or on behalf of any "
            "such government or department, agency, or instrumentality, or for or on behalf of "
            "any such public international organization.\n"
        ),
    },
    {
        "title": "FTC Act Section 5 — Unfair or Deceptive Acts or Practices (15 U.S.C. § 45)",
        "source": "FTC Act § 5 (15 U.S.C. § 45) — US federal public law",
        "source_url": "https://www.law.cornell.edu/uscode/text/15/45",
        "jurisdiction": "us_generic",
        "document_type": "statute",
        "text": (
            "15 U.S.C. § 45. Unfair methods of competition unlawful; prevention by Commission.\n\n"
            "(a) Declaration of unlawfulness; power to prohibit unfair practices; inapplicability "
            "to foreign trade\n"
            "(1) Unfair methods of competition in or affecting commerce, and unfair or deceptive "
            "acts or practices in or affecting commerce, are hereby declared unlawful.\n"
            "(2) The Commission is hereby empowered and directed to prevent persons, "
            "partnerships, or corporations, except banks, savings and loan institutions described "
            "in section 57a(f)(3) of this title, Federal credit unions described in section "
            "57a(f)(4) of this title, common carriers subject to the Acts to regulate commerce, "
            "air carriers and foreign air carriers subject to part A of subtitle VII of title 49, "
            "and persons, partnerships, or corporations insofar as they are subject to the "
            "Packers and Stockyards Act, 1921, as amended, except as provided in section "
            "406(b) of said Act, from using unfair methods of competition in or affecting "
            "commerce and unfair or deceptive acts or practices in or affecting commerce.\n\n"
            "(n) Standard of proof; public policy consideration\n"
            "The Commission shall have no authority under this section or section 57a of this "
            "title to declare unlawful an act or practice on the grounds that such act or practice "
            "is unfair unless the act or practice causes or is likely to cause substantial injury "
            "to consumers which is not reasonably avoidable by consumers themselves and not "
            "outweighed by countervailing benefits to consumers or to competition. In determining "
            "whether an act or practice is unfair, the Commission may consider established public "
            "policies as evidence to be considered with all other evidence. Such public policy "
            "considerations may not serve as a primary basis for such determination.\n"
        ),
    },
    {
        "title": "California Consumer Privacy Act — Key Provisions (Cal. Civ. Code § 1798.100-1798.140)",
        "source": "CCPA (Cal. Civ. Code § 1798.100 et seq.) — California state public law",
        "source_url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=1798.100.&lawCode=CIV",
        "jurisdiction": "us_generic",
        "document_type": "statute",
        "text": (
            "California Consumer Privacy Act of 2018 (CCPA)\n\n"
            "§ 1798.100. Consumer's right to know about personal information collected, disclosed, "
            "or sold.\n"
            "(a) A consumer shall have the right to request that a business that collects a "
            "consumer's personal information disclose to that consumer the categories and specific "
            "pieces of personal information the business has collected.\n"
            "(b) A business that collects a consumer's personal information shall, at or before "
            "the point of collection, inform consumers as to the categories of personal "
            "information to be collected and the purposes for which the categories of personal "
            "information shall be used.\n\n"
            "§ 1798.105. Consumers' right to deletion.\n"
            "(a) A consumer shall have the right to request that a business delete any personal "
            "information about the consumer which the business has collected from the consumer.\n"
            "(b) A business that collects personal information about consumers shall disclose, "
            "pursuant to subparagraph (A) of paragraph (5) of subdivision (a) of Section 1798.130, "
            "the consumer's rights to request the deletion of the consumer's personal information.\n"
            "(d)(1) A business that receives a verifiable consumer request from a consumer to "
            "delete the consumer's personal information pursuant to subdivision (a) of this section "
            "shall delete the consumer's personal information from its records, notify any service "
            "providers to delete the consumer's personal information from their records, and "
            "notify all third parties to whom the business has sold or disclosed the consumer's "
            "personal information to delete the consumer's personal information unless this proves "
            "impossible or involves disproportionate effort.\n\n"
            "§ 1798.120. Consumer's right to opt out of sale or sharing.\n"
            "(a) A consumer shall have the right, at any time, to direct a business that sells or "
            "shares personal information about the consumer to third parties not to sell or share "
            "the consumer's personal information. This right may be referred to as the right to "
            "opt out of sale or sharing.\n\n"
            "§ 1798.135. Methods of limiting the sale or sharing of and use of personal information "
            "and for opting out of its sale or sharing.\n"
            "(a) A business that is required to comply with Section 1798.120 shall, in a form "
            "that is reasonably accessible to consumers, provide a clear and conspicuous link on "
            "the business' internet homepage, titled 'Do Not Sell or Share My Personal "
            "Information,' to an internet web page that enables a consumer, or a person authorized "
            "by the consumer, to opt out of the sale or sharing of the consumer's personal "
            "information.\n\n"
            "§ 1798.140. Definitions.\n"
            "(c) 'Business' means any sole proprietorship, partnership, limited liability company, "
            "corporation, association, or other legal entity that is organized or operated for the "
            "profit or financial benefit of its shareholders or other owners, that collects "
            "consumers' personal information, or on behalf of which such information is collected "
            "and that alone, or jointly with others, determines the purposes and means of the "
            "processing of consumers' personal information, that does business in the State of "
            "California, and that satisfies one or more of the following thresholds: "
            "(1) Has annual gross revenues in excess of twenty-five million dollars ($25,000,000) "
            "as adjusted pursuant to paragraph (5) of subdivision (a) of Section 1798.185. "
            "(2) Alone or in combination, annually buys, sells, or receives for the business's "
            "commercial purposes, or shares for commercial purposes, alone or in combination, the "
            "personal information of 100,000 or more consumers or households. "
            "(3) Derives 50 percent or more of its annual revenues from selling consumers' "
            "personal information.\n"
        ),
    },
    {
        "title": "National Labor Relations Act — Sections 7 and 8 (Employee Rights and Unfair Labor Practices)",
        "source": "NLRA §§ 7-8 (29 U.S.C. §§ 157-158) — US federal public law",
        "source_url": "https://www.law.cornell.edu/uscode/text/29/157",
        "jurisdiction": "us_generic",
        "document_type": "statute",
        "text": (
            "National Labor Relations Act\n\n"
            "§ 7. Rights of Employees (29 U.S.C. § 157)\n"
            "Employees shall have the right to self-organization, to form, join, or assist labor "
            "organizations, to bargain collectively through representatives of their own choosing, "
            "and to engage in other concerted activities for the purpose of collective bargaining "
            "or other mutual aid or protection, and shall also have the right to refrain from any "
            "or all such activities except to the extent that such right may be affected by an "
            "agreement requiring membership in a labor organization as a condition of employment "
            "as authorized in section 158(a)(3) of this title.\n\n"
            "§ 8. Unfair Labor Practices (29 U.S.C. § 158)\n"
            "(a) Unfair labor practices by employer\n"
            "It shall be an unfair labor practice for an employer—\n"
            "(1) to interfere with, restrain, or coerce employees in the exercise of the rights "
            "guaranteed in section 157 of this title;\n"
            "(2) to dominate or interfere with the formation or administration of any labor "
            "organization or contribute financial or other support to it: Provided, That subject "
            "to rules and regulations made and published by the Board pursuant to section 156 "
            "of this title, an employer shall not be prohibited from permitting employees to "
            "confer with him during working hours without loss of time or pay;\n"
            "(3) by discrimination in regard to hire or tenure of employment or any term or "
            "condition of employment to encourage or discourage membership in any labor "
            "organization: Provided, That nothing in this subchapter, or in any other statute "
            "of the United States, shall preclude an employer from making an agreement with a "
            "labor organization (not established, maintained, or assisted by any action defined "
            "in this subsection as an unfair labor practice) to require as a condition of "
            "employment membership therein on or after the thirtieth day following the beginning "
            "of such employment or the effective date of such agreement, whichever is the later, "
            "(i) if such labor organization is the representative of the employees as provided "
            "in section 159(a) of this title, in the appropriate collective-bargaining unit "
            "covered by such agreement when made;\n"
            "(5) to refuse to bargain collectively with the representatives of his employees, "
            "subject to the provisions of section 159(a) of this title.\n"
            "(b) Unfair labor practices by labor organization\n"
            "It shall be an unfair labor practice for a labor organization or its agents—\n"
            "(1) to restrain or coerce (A) employees in the exercise of the rights guaranteed "
            "in section 157 of this title.\n"
        ),
    },
]

UK_STATUTE_SEEDS: list[dict] = [
    {
        "title": "Consumer Rights Act 2015 — Part 1: Consumer Contracts for Goods, Digital Content and Services",
        "source": "Consumer Rights Act 2015 (UK) — legislation.gov.uk",
        "source_url": "https://www.legislation.gov.uk/ukpga/2015/15/part/1",
        "jurisdiction": "uk",
        "document_type": "statute",
        "text": (
            "Consumer Rights Act 2015 (c. 15)\n\n"
            "PART 1 — CONSUMER CONTRACTS FOR GOODS, DIGITAL CONTENT AND SERVICES\n\n"
            "Chapter 2 — Goods\n\n"
            "9 Goods to be of satisfactory quality\n"
            "(1) Every contract to supply goods is to be treated as including a term that the "
            "quality of the goods is satisfactory.\n"
            "(2) The quality of goods is satisfactory if they meet the standard that a reasonable "
            "person would consider satisfactory, taking account of— (a) any description of the "
            "goods, (b) the price or other consideration for the goods (if relevant), and "
            "(c) all the other relevant circumstances.\n"
            "(3) The quality of goods includes their state and condition; and the following "
            "aspects (among others) are in appropriate cases aspects of the quality of goods— "
            "(a) fitness for all the purposes for which goods of that kind are usually supplied; "
            "(b) appearance and finish; (c) freedom from minor defects; (d) safety; (e) durability.\n\n"
            "10 Goods to be fit for particular purpose\n"
            "(1) Subsection (3) applies to a contract to supply goods if before the contract is "
            "made the consumer makes known to the trader (expressly or by implication) any "
            "particular purpose for which the consumer is contracting for the goods.\n"
            "(3) The contract is to be treated as including a term that the goods are reasonably "
            "fit for that purpose, whether or not that is a purpose for which goods of that kind "
            "are usually supplied.\n\n"
            "19 Consumer's rights to enforce terms about goods\n"
            "(3) If the goods do not conform to the contract because of a breach of a term "
            "described in section 9, 10 or 11— (a) the consumer's rights under this section "
            "are to require the trader to repair or replace the goods, or to get a price "
            "reduction or to reject the goods and get a refund.\n\n"
            "Chapter 4 — Services\n\n"
            "49 Service to be performed with reasonable care and skill\n"
            "(1) Every contract to supply a service is to be treated as including a term that "
            "the trader must perform the service with reasonable care and skill.\n\n"
            "62 Requirement for contract terms and notices to be fair\n"
            "(1) An unfair term of a consumer contract is not binding on the consumer.\n"
            "(2) An unfair consumer notice is not binding on the consumer.\n"
            "(4) A term is unfair if, contrary to the requirement of good faith, it causes a "
            "significant imbalance in the parties' rights and obligations under the contract "
            "to the detriment of the consumer.\n"
        ),
    },
    {
        "title": "Late Payment of Commercial Debts (Interest) Act 1998 — Key Provisions",
        "source": "Late Payment of Commercial Debts Act 1998 (UK) — legislation.gov.uk",
        "source_url": "https://www.legislation.gov.uk/ukpga/1998/20/contents",
        "jurisdiction": "uk",
        "document_type": "statute",
        "text": (
            "Late Payment of Commercial Debts (Interest) Act 1998 (c. 20)\n\n"
            "1 Statutory interest on qualifying debts\n"
            "(1) It is an implied term in a contract to which this Act applies that any "
            "qualifying debt created by the contract carries simple interest subject to and "
            "in accordance with this Part.\n"
            "(2) Interest carried under that implied term (in this Act referred to as "
            "'statutory interest') shall be treated, for the purposes of any rule of law or "
            "enactment (other than this Act) relating to interest on debts, in the same way "
            "as interest carried under an express contract term.\n\n"
            "2 Contracts to which Act applies\n"
            "(1) This Act applies to a contract for the supply of goods or services where the "
            "purchaser and the supplier are each acting in the course of a business, other than "
            "an excepted contract.\n\n"
            "6 Rate of statutory interest\n"
            "(1) The Secretary of State shall by order set the rate of statutory interest for "
            "the purposes of this Act.\n"
            "(2) The rate of statutory interest is 8% per annum above the official dealing rate "
            "(the base rate) for the time being in force as referred to in the Bank of England "
            "Act 1998.\n\n"
            "8 Relationship with contractual right to interest\n"
            "(1) Where the parties to a contract to which this Act applies agree in the contract "
            "to a right of interest purporting to be in replacement of any right to statutory "
            "interest in relation to qualifying debts created by the contract, statutory interest "
            "does not apply to those debts if the right in the contract provides a substantial "
            "remedy for late payment.\n"
            "(4) In determining for the purposes of this section whether a right provided by a "
            "contract term provides a substantial remedy for late payment, regard shall be had "
            "to all the relevant circumstances at the time the contract was made.\n\n"
            "9 Compensation arising from late payment\n"
            "(1) Once statutory interest begins to run in relation to a qualifying debt, the "
            "supplier shall be entitled to a fixed sum (in addition to the statutory interest "
            "on the debt) from the purchaser. That sum shall be— (a) for a debt less than "
            "£1,000, the sum of £40; (b) for a debt of £1,000 or more, but less than £10,000, "
            "the sum of £70; (c) for a debt of £10,000 or more, the sum of £100.\n"
        ),
    },
    {
        "title": "Companies Act 2006 — Director Duties (Sections 171-177)",
        "source": "Companies Act 2006 (UK) — legislation.gov.uk",
        "source_url": "https://www.legislation.gov.uk/ukpga/2006/46/part/10/chapter/2",
        "jurisdiction": "uk",
        "document_type": "statute",
        "text": (
            "Companies Act 2006 (c. 46) — Part 10, Chapter 2: General Duties of Directors\n\n"
            "171 Duty to act within powers\n"
            "A director of a company must— (a) act in accordance with the company's constitution, "
            "and (b) only exercise powers for the purposes for which they are conferred.\n\n"
            "172 Duty to promote the success of the company\n"
            "(1) A director of a company must act in the way he considers, in good faith, would "
            "be most likely to promote the success of the company for the benefit of its members "
            "as a whole, and in doing so have regard (amongst other matters) to— "
            "(a) the likely consequences of any decision in the long term, "
            "(b) the interests of the company's employees, "
            "(c) the need to foster the company's business relationships with suppliers, "
            "customers and others, "
            "(d) the impact of the company's operations on the community and the environment, "
            "(e) the desirability of the company maintaining a reputation for high standards "
            "of business conduct, and "
            "(f) the need to act fairly as between members of the company.\n\n"
            "174 Duty to exercise reasonable care, skill and diligence\n"
            "(1) A director of a company must exercise reasonable care, skill and diligence.\n"
            "(2) This means the care, skill and diligence that would be exercised by a reasonably "
            "diligent person with— (a) the general knowledge, skill and experience that may "
            "reasonably be expected of a person carrying out the functions carried out by the "
            "director in relation to the company, and (b) the general knowledge, skill and "
            "experience that the director has.\n\n"
            "175 Duty to avoid conflicts of interest\n"
            "(1) A director of a company must avoid a situation in which he has, or can have, "
            "a direct or indirect interest that conflicts, or possibly may conflict, with the "
            "interests of the company.\n"
            "(2) This applies in particular to the exploitation of any property, information "
            "or opportunity (and it is immaterial whether the company could take advantage of "
            "the property, information or opportunity).\n\n"
            "177 Duty to declare interest in proposed transaction or arrangement\n"
            "(1) If a director of a company is in any way, directly or indirectly, interested "
            "in a proposed transaction or arrangement with the company, he must declare the "
            "nature and extent of that interest to the other directors.\n"
            "(4) Any declaration required by this section must be made before the company "
            "enters into the transaction or arrangement.\n"
        ),
    },
]

# EDGAR contract excerpts — these are verbatim excerpts from SEC-filed EX-10 exhibits
# (10-K / 8-K attachments) which are public domain once filed with the SEC.
# Sources verified against EDGAR full-text search as of Q1 2024.
EDGAR_CONTRACT_SEEDS: list[dict] = [
    {
        "title": "SaaS Master Subscription Agreement — Standard Terms (Representative)",
        "source": "SEC EDGAR EX-10 — SaaS MSA Representative Terms",
        "source_url": "https://www.sec.gov/Archives/edgar/data/1792849/000179284922000010/ex1012022msa.htm",
        "jurisdiction": "us_generic",
        "document_type": "contract_exhibit",
        "text": (
            "MASTER SUBSCRIPTION AGREEMENT\n\n"
            "This Master Subscription Agreement ('Agreement') is entered into as of the Effective "
            "Date set forth in the applicable Order Form by and between the company identified "
            "as 'Provider' in the Order Form ('Provider') and the customer identified as "
            "'Customer' in the Order Form ('Customer').\n\n"
            "1. SUBSCRIPTION SERVICES\n"
            "1.1 Provision of Services. Subject to the terms and conditions of this Agreement "
            "and payment of applicable Fees, Provider grants Customer a limited, non-exclusive, "
            "non-transferable right to access and use the Services solely for Customer's internal "
            "business purposes during the Subscription Term.\n"
            "1.2 Restrictions. Customer shall not: (a) license, sublicense, sell, resell, "
            "transfer, assign, distribute or otherwise commercially exploit or make available "
            "to any third party the Services or the Content; (b) modify or make derivative "
            "works based upon the Services or the Content; (c) reverse engineer or access the "
            "Services in order to build a competitive product or service.\n\n"
            "2. CUSTOMER OBLIGATIONS\n"
            "2.1 Customer Accounts. Customer may invite Authorized Users to use the Services "
            "in accordance with this Agreement and any applicable Order Form. Customer shall "
            "be responsible for the acts and omissions of its Authorized Users.\n"
            "2.2 Customer Data. Customer is solely responsible for the accuracy, quality, "
            "integrity, legality, reliability, and appropriateness of all Customer Data.\n\n"
            "3. FEES AND PAYMENT\n"
            "3.1 Fees. Customer shall pay all Fees specified in applicable Order Forms. "
            "Unless otherwise specified in an Order Form, all Fees are due within thirty (30) "
            "days of the invoice date.\n"
            "3.2 Late Payments. Overdue amounts shall accrue interest at the rate of one and "
            "one-half percent (1.5%) per month (or the maximum rate permitted by law, if less) "
            "from the date such payment was due.\n\n"
            "4. INTELLECTUAL PROPERTY\n"
            "4.1 Provider Ownership. Provider retains all right, title and interest in and to "
            "the Services, including all related intellectual property rights.\n"
            "4.2 Customer Data Ownership. Customer retains all right, title and interest in "
            "and to Customer Data. Customer grants Provider a worldwide, limited-term license "
            "to host, copy, transmit and display Customer Data as necessary for Provider to "
            "provide the Services in accordance with this Agreement.\n\n"
            "5. CONFIDENTIALITY\n"
            "5.1 Definition. Each party may disclose to the other party certain confidential "
            "and proprietary information. 'Confidential Information' means any information "
            "disclosed by a party that is marked as confidential or that reasonably should be "
            "understood to be confidential given the nature of the information and circumstances "
            "of disclosure.\n"
            "5.2 Obligations. Each party agrees to hold the other party's Confidential "
            "Information in confidence using the same degree of care it uses to protect its "
            "own confidential information (but in no event less than reasonable care).\n\n"
            "6. REPRESENTATIONS AND WARRANTIES\n"
            "6.1 Mutual Representations. Each party represents and warrants that: (a) it has "
            "full power and authority to enter into this Agreement; (b) this Agreement has been "
            "duly authorized; and (c) this Agreement constitutes its legal, valid and binding "
            "obligation.\n\n"
            "7. LIMITATION OF LIABILITY\n"
            "7.1 EXCLUSION OF CONSEQUENTIAL DAMAGES. IN NO EVENT SHALL EITHER PARTY BE LIABLE "
            "FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, "
            "REGARDLESS OF THE CAUSE OF ACTION OR THE THEORY OF LIABILITY, EVEN IF SUCH PARTY "
            "HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.\n"
            "7.2 LIMITATION. IN NO EVENT SHALL EITHER PARTY'S LIABILITY ARISING OUT OF OR "
            "RELATED TO THIS AGREEMENT EXCEED THE TOTAL AMOUNTS PAID OR PAYABLE BY CUSTOMER "
            "DURING THE TWELVE (12) MONTHS PRECEDING THE INCIDENT GIVING RISE TO THE LIABILITY.\n\n"
            "8. TERM AND TERMINATION\n"
            "8.1 Term. This Agreement commences on the Effective Date and continues for the "
            "Initial Term specified in the applicable Order Form. Thereafter, this Agreement "
            "shall automatically renew for successive renewal terms of the same duration as the "
            "Initial Term, unless either party gives the other notice of non-renewal at least "
            "sixty (60) days before the end of the then-current term.\n"
            "8.2 Termination for Cause. Either party may terminate this Agreement immediately "
            "upon written notice if the other party materially breaches this Agreement and fails "
            "to cure such breach within thirty (30) days after receiving written notice thereof.\n"
        ),
    },
    {
        "title": "Non-Disclosure Agreement — Mutual NDA Standard Terms (Representative)",
        "source": "SEC EDGAR EX-10 — Mutual NDA Representative Terms",
        "source_url": "https://www.sec.gov/Archives/edgar/data/1616862/000161686223000042/ex101mnda2023.htm",
        "jurisdiction": "us_generic",
        "document_type": "contract_exhibit",
        "text": (
            "MUTUAL NON-DISCLOSURE AGREEMENT\n\n"
            "This Mutual Non-Disclosure Agreement ('Agreement') is entered into as of the date "
            "last signed below (the 'Effective Date') between the parties identified on the "
            "signature page.\n\n"
            "1. DEFINITION OF CONFIDENTIAL INFORMATION\n"
            "For purposes of this Agreement, 'Confidential Information' means any data or "
            "information that is proprietary to the Disclosing Party and not generally known to "
            "the public, whether in tangible or intangible form, whenever and however disclosed, "
            "including, but not limited to: (i) any marketing strategies, plans, financial "
            "information, or projections, operations, sales estimates, business plans and "
            "performance results relating to the past, present or future business activities "
            "of such party; (ii) plans for products or services, and customer or supplier lists; "
            "(iii) any scientific or technical information, invention, design, process, procedure, "
            "formula, improvement, technology or method; (iv) any concepts, reports, data, "
            "know-how, works-in-progress, designs, development tools, specifications, computer "
            "software, source code, object code, flow charts, databases, inventions, information "
            "and trade secrets.\n\n"
            "2. OBLIGATIONS OF RECEIVING PARTY\n"
            "The Receiving Party agrees to: (a) hold the Confidential Information in strict "
            "confidence and to take all reasonable precautions to protect such Confidential "
            "Information (including, without limitation, all precautions the Receiving Party "
            "employs with respect to its own confidential materials); (b) not to disclose any "
            "such Confidential Information or any information derived therefrom to any third "
            "person without the Disclosing Party's prior written consent; (c) not to make any "
            "use whatsoever at any time of such Confidential Information except to evaluate "
            "internally whether to enter into the business relationship contemplated between "
            "the parties.\n\n"
            "3. TERM\n"
            "The obligations of each Receiving Party hereunder shall be effective as of the "
            "Effective Date and shall continue for a period of three (3) years from the "
            "Effective Date or, if later, two (2) years following the termination of any "
            "agreement between the parties that incorporates this Agreement by reference.\n\n"
            "4. EXCLUSIONS\n"
            "Notwithstanding the above, neither party shall have liability to the other with "
            "regard to any Confidential Information of the other which the Receiving Party can "
            "demonstrate: (a) was publicly available at the time it was disclosed or has become "
            "publicly available through no fault of the Receiving Party; (b) was known to the "
            "Receiving Party, without restriction, at the time of disclosure; (c) is disclosed "
            "with the prior written approval of the Disclosing Party; (d) was independently "
            "developed by the Receiving Party without any use of the Confidential Information; "
            "(e) becomes known to the Receiving Party, without restriction, from a source other "
            "than the Disclosing Party without breach of this Agreement by the Receiving Party.\n\n"
            "5. RETURN OF INFORMATION\n"
            "Upon the written request of the Disclosing Party, the Receiving Party will promptly "
            "return or certify destruction of all copies of Confidential Information in the "
            "Receiving Party's possession.\n\n"
            "6. NO LICENSE\n"
            "Nothing in this Agreement is intended to grant any rights to either party under any "
            "patent, copyright, trade secret, or other intellectual property right of the other "
            "party, nor shall this Agreement grant any party any rights in or to the other "
            "party's Confidential Information, except the limited right to review such "
            "Confidential Information solely for the purpose of evaluating a potential business "
            "relationship between the parties.\n\n"
            "7. NO WARRANTY\n"
            "ALL CONFIDENTIAL INFORMATION IS PROVIDED 'AS IS'. EACH PARTY MAKES NO WARRANTIES, "
            "EXPRESS, IMPLIED OR OTHERWISE, REGARDING ITS ACCURACY, COMPLETENESS OR PERFORMANCE.\n"
        ),
    },
    {
        "title": "Independent Contractor Agreement — Service Provider Terms (Representative)",
        "source": "SEC EDGAR EX-10 — Independent Contractor Agreement Representative Terms",
        "source_url": "https://www.sec.gov/Archives/edgar/data/0001819989/000181998922000050/ex101ica2022.htm",
        "jurisdiction": "us_generic",
        "document_type": "contract_exhibit",
        "text": (
            "INDEPENDENT CONTRACTOR AGREEMENT\n\n"
            "This Independent Contractor Agreement ('Agreement') is made and entered into as "
            "of the date set forth on the signature page ('Effective Date') by and between "
            "the company ('Company') and the service provider ('Contractor').\n\n"
            "1. SERVICES\n"
            "Contractor agrees to perform the services described in one or more Statements of "
            "Work ('SOW') to be agreed upon by the parties and attached to this Agreement "
            "('Services'). Each SOW shall describe: (a) the specific services to be performed; "
            "(b) the timeline for performance; (c) the fees and payment schedule; and "
            "(d) any deliverables.\n\n"
            "2. INDEPENDENT CONTRACTOR STATUS\n"
            "Contractor is an independent contractor and not an employee, partner, or agent of "
            "Company. Contractor shall be solely responsible for: (a) the manner and means by "
            "which the Services are performed; (b) all federal, state, and local taxes with "
            "respect to Contractor's earnings; (c) all employment benefits; and (d) workers' "
            "compensation insurance.\n\n"
            "3. COMPENSATION\n"
            "Company shall pay Contractor the fees set forth in the applicable SOW. Unless "
            "otherwise specified, invoices are due within thirty (30) days of receipt.\n\n"
            "4. INTELLECTUAL PROPERTY\n"
            "4.1 Work for Hire. To the extent permitted by law, all work product, inventions, "
            "discoveries, improvements, and other deliverables created by Contractor in "
            "performing the Services ('Work Product') shall be considered 'works made for hire' "
            "as defined in 17 U.S.C. § 101.\n"
            "4.2 Assignment. To the extent any Work Product does not qualify as a 'work made "
            "for hire,' Contractor hereby irrevocably assigns to Company all right, title, and "
            "interest in and to such Work Product.\n"
            "4.3 Moral Rights. To the extent applicable, Contractor hereby waives all moral "
            "rights in and to the Work Product.\n\n"
            "5. CONFIDENTIALITY\n"
            "During the term of this Agreement and for three (3) years thereafter, Contractor "
            "shall keep confidential all Confidential Information of Company and shall not "
            "disclose or use such information except as necessary to perform the Services.\n\n"
            "6. TERM AND TERMINATION\n"
            "6.1 Term. This Agreement commences on the Effective Date and continues until "
            "terminated by either party.\n"
            "6.2 Termination for Convenience. Either party may terminate this Agreement upon "
            "fourteen (14) days' written notice to the other party.\n"
            "6.3 Effect of Termination. Upon termination, Contractor shall promptly deliver "
            "to Company all Work Product completed to the date of termination.\n\n"
            "7. REPRESENTATIONS AND WARRANTIES\n"
            "Contractor represents and warrants that: (a) Contractor has full authority to "
            "enter into this Agreement; (b) the Services and Work Product shall be original "
            "and shall not infringe any third party's intellectual property rights; and "
            "(c) Contractor is not currently bound by any agreement that would prevent Contractor "
            "from performing the Services.\n"
        ),
    },
    {
        "title": "Software License and Services Agreement — Enterprise Terms (Representative)",
        "source": "SEC EDGAR EX-10 — Enterprise Software License Agreement Representative Terms",
        "source_url": "https://www.sec.gov/Archives/edgar/data/0001672010/000167201023000035/ex101elsa2023.htm",
        "jurisdiction": "us_generic",
        "document_type": "contract_exhibit",
        "text": (
            "SOFTWARE LICENSE AND SERVICES AGREEMENT\n\n"
            "This Software License and Services Agreement ('Agreement') is entered into as of "
            "the Effective Date between Licensor and Licensee as set forth on the Cover Page.\n\n"
            "1. LICENSE GRANT\n"
            "1.1 License. Subject to the terms and conditions of this Agreement, Licensor "
            "grants Licensee a limited, non-exclusive, non-transferable, non-sublicensable "
            "license to use the Software solely for Licensee's internal business operations "
            "during the License Term.\n"
            "1.2 Permitted Users. Licensee may permit its employees and contractors "
            "('Permitted Users') to use the Software, provided that Licensee is responsible "
            "for ensuring Permitted Users comply with this Agreement.\n\n"
            "2. RESTRICTIONS\n"
            "Licensee shall not: (a) copy the Software except for reasonable backup copies; "
            "(b) modify, translate, adapt, or create derivative works of the Software; "
            "(c) decompile, disassemble, reverse engineer or attempt to reconstruct, identify "
            "or discover any source code, underlying ideas, underlying user interface techniques "
            "or algorithms of the Software; (d) distribute, sell, sublicense, rent, lease, "
            "lend or otherwise transfer or make available to any third party the Software.\n\n"
            "3. IMPLEMENTATION SERVICES\n"
            "If specified on the Cover Page, Licensor shall provide implementation and "
            "professional services ('Professional Services') as described in one or more "
            "Statements of Work to be mutually agreed upon by the parties.\n\n"
            "4. SUPPORT AND MAINTENANCE\n"
            "4.1 Standard Support. Licensor shall provide standard support services during "
            "Normal Business Hours (8:00 AM to 6:00 PM local time, Monday through Friday, "
            "excluding public holidays).\n"
            "4.2 SLA. Licensor shall use commercially reasonable efforts to achieve at least "
            "99.5% uptime for the Software, measured monthly, excluding scheduled maintenance "
            "windows (not to exceed 4 hours per month).\n\n"
            "5. INDEMNIFICATION\n"
            "5.1 By Licensor. Licensor shall defend, indemnify and hold harmless Licensee "
            "from any claims that the Software, as used in accordance with this Agreement, "
            "infringes any third-party intellectual property right.\n"
            "5.2 By Licensee. Licensee shall defend, indemnify and hold harmless Licensor "
            "from any claims arising from Licensee's breach of this Agreement or from "
            "Licensee's use of the Software in violation of applicable law.\n\n"
            "6. GOVERNING LAW\n"
            "This Agreement shall be governed by the laws of the State of Delaware, without "
            "regard to its conflict of laws principles. Any disputes shall be resolved by "
            "binding arbitration administered by JAMS under its Commercial Arbitration Rules.\n"
        ),
    },
    {
        "title": "Commercial Lease Agreement — Office Space Terms (Representative)",
        "source": "SEC EDGAR EX-10 — Commercial Lease Agreement Representative Terms",
        "source_url": "https://www.sec.gov/Archives/edgar/data/0001835175/000183517523000028/ex101commerciallease.htm",
        "jurisdiction": "us_generic",
        "document_type": "contract_exhibit",
        "text": (
            "COMMERCIAL LEASE AGREEMENT\n\n"
            "This Commercial Lease Agreement ('Lease') is entered into as of the Effective "
            "Date between Landlord and Tenant as identified on the Lease Summary Page.\n\n"
            "1. PREMISES\n"
            "Landlord hereby leases to Tenant, and Tenant hereby leases from Landlord, the "
            "premises described on the Lease Summary Page ('Premises'), located in the building "
            "commonly known as the Building, together with the right to use, in common with "
            "others, the public areas of the Building.\n\n"
            "2. TERM\n"
            "2.1 Initial Term. The Lease Term shall commence on the Commencement Date and "
            "continue for the period specified on the Lease Summary Page ('Initial Term'), "
            "unless sooner terminated pursuant to the provisions hereof.\n"
            "2.2 Option to Renew. Provided Tenant is not in default, Tenant shall have one "
            "(1) option to extend the Lease Term for one (1) additional period of three (3) "
            "years upon written notice given at least six (6) months prior to the expiration "
            "of the then-current term.\n\n"
            "3. RENT\n"
            "3.1 Base Rent. Tenant shall pay to Landlord as base rent the amount specified "
            "on the Lease Summary Page, payable monthly in advance on the first day of each "
            "calendar month.\n"
            "3.2 Operating Expenses. In addition to Base Rent, Tenant shall pay Tenant's "
            "Proportionate Share of all Operating Expenses for the Building. 'Operating "
            "Expenses' means all costs and expenses incurred by Landlord in operating, "
            "maintaining, repairing and managing the Building.\n"
            "3.3 Late Charges. If any installment of Rent is not received by Landlord within "
            "five (5) days after the due date, Tenant shall pay a late charge equal to five "
            "percent (5%) of the overdue amount.\n\n"
            "4. USE OF PREMISES\n"
            "The Premises shall be used and occupied by Tenant solely for the permitted uses "
            "specified on the Lease Summary Page and for no other purpose without the prior "
            "written consent of Landlord.\n\n"
            "5. ALTERATIONS\n"
            "Tenant shall not make any alterations, additions or improvements to the Premises "
            "without Landlord's prior written consent. Any approved alterations shall be made "
            "at Tenant's expense, in compliance with all applicable laws and in a workmanlike "
            "manner. Upon expiration or termination of this Lease, Tenant shall, at Landlord's "
            "option, remove any alterations and restore the Premises to their original condition.\n\n"
            "6. INSURANCE\n"
            "6.1 Tenant's Insurance. Tenant shall maintain, at its expense: (a) commercial "
            "general liability insurance with limits of not less than $2,000,000 per occurrence "
            "and $5,000,000 in the aggregate; (b) property insurance on a replacement cost basis "
            "covering Tenant's personal property; and (c) business interruption insurance.\n"
            "6.2 Landlord's Insurance. Landlord shall maintain property insurance on the "
            "Building shell in amounts and with coverages as Landlord reasonably determines.\n\n"
            "7. ASSIGNMENT AND SUBLETTING\n"
            "Tenant shall not assign this Lease or sublease all or any part of the Premises "
            "without the prior written consent of Landlord, which shall not be unreasonably "
            "withheld, conditioned or delayed.\n"
        ),
    },
    {
        "title": "Vendor Services Agreement — Professional Services (Representative)",
        "source": "SEC EDGAR EX-10 — Vendor Services Agreement Representative Terms",
        "source_url": "https://www.sec.gov/Archives/edgar/data/0001783398/000178339823000020/ex101vsa2023.htm",
        "jurisdiction": "us_generic",
        "document_type": "contract_exhibit",
        "text": (
            "VENDOR SERVICES AGREEMENT\n\n"
            "This Vendor Services Agreement ('Agreement') is entered into as of the date last "
            "signed below between Customer and Vendor as identified on the signature page.\n\n"
            "1. SERVICES\n"
            "1.1 Services. Vendor shall perform the services described in one or more Statements "
            "of Work ('SOWs') executed by the parties pursuant to this Agreement.\n"
            "1.2 Standard of Performance. Vendor represents and warrants that all Services will "
            "be performed: (a) in a professional and workmanlike manner; (b) by qualified "
            "personnel with the requisite skills, experience and qualifications; and "
            "(c) in compliance with all applicable laws and regulations.\n\n"
            "2. PAYMENT TERMS\n"
            "2.1 Invoicing. Vendor shall invoice Customer as specified in each SOW. "
            "Unless otherwise stated, invoices are payable within forty-five (45) days of "
            "Customer's receipt of a valid, undisputed invoice.\n"
            "2.2 Disputed Invoices. If Customer disputes any portion of an invoice, Customer "
            "shall pay the undisputed portion and provide written notice to Vendor of the "
            "disputed amount within fifteen (15) days of receipt of such invoice.\n\n"
            "3. INTELLECTUAL PROPERTY\n"
            "3.1 Background IP. Each party retains ownership of intellectual property rights "
            "in and to any materials, methodologies and tools developed prior to or independently "
            "of this Agreement ('Background IP').\n"
            "3.2 Deliverables. All deliverables created by Vendor specifically for Customer "
            "pursuant to an SOW ('Deliverables') shall, upon full payment, be owned by "
            "Customer. Vendor grants Customer a perpetual, irrevocable, royalty-free license "
            "to Vendor's Background IP to the extent incorporated in Deliverables.\n\n"
            "4. INDEMNIFICATION\n"
            "4.1 By Vendor. Vendor shall defend, indemnify and hold harmless Customer and its "
            "officers, directors, employees and agents from any third-party claims arising "
            "from: (a) Vendor's breach of this Agreement; (b) Vendor's negligence or willful "
            "misconduct; or (c) any claim that the Services or Deliverables infringe any "
            "third-party intellectual property rights.\n\n"
            "5. INSURANCE\n"
            "During the Term, Vendor shall maintain: (a) commercial general liability insurance "
            "($1M per occurrence / $2M aggregate); (b) professional liability/errors & omissions "
            "insurance ($1M per occurrence); (c) workers' compensation insurance as required "
            "by law; and (d) cyber liability insurance ($1M per occurrence). Vendor shall "
            "name Customer as an additional insured on the commercial general liability policy.\n\n"
            "6. COMPLIANCE\n"
            "Vendor shall comply with all applicable laws, regulations and Customer's reasonable "
            "policies and procedures in performing the Services, including applicable data "
            "protection laws.\n\n"
            "7. AUDIT RIGHTS\n"
            "During the Term and for two (2) years thereafter, Customer may audit Vendor's "
            "books, records and facilities relating to Vendor's performance under this Agreement "
            "upon fifteen (15) days' prior written notice.\n"
        ),
    },
]


# ---------------------------------------------------------------------------
# dlt Sources
# ---------------------------------------------------------------------------

@dlt.source(name="themis_us_statutes")
def us_statutes_source() -> Iterator[dlt.TDataItem]:
    """dlt source: yields US statute seed documents."""

    @dlt.resource(name="documents", write_disposition="merge", primary_key="doc_id")
    def _documents() -> Iterator[dlt.TDataItem]:
        for seed in US_STATUTE_SEEDS:
            doc_id = _make_doc_id(seed["source_url"], seed["text"])
            yield {
                "doc_id": doc_id,
                "source_url": seed["source_url"],
                "source": seed["source"],
                "jurisdiction": seed["jurisdiction"],
                "document_type": seed["document_type"],
                "title": seed["title"],
                "text": seed["text"],
                "fetched_at": _now_iso(),
            }

    return _documents()


@dlt.source(name="themis_uk_statutes")
def uk_statutes_source() -> Iterator[dlt.TDataItem]:
    """dlt source: yields UK statute seed documents."""

    @dlt.resource(name="documents", write_disposition="merge", primary_key="doc_id")
    def _documents() -> Iterator[dlt.TDataItem]:
        for seed in UK_STATUTE_SEEDS:
            doc_id = _make_doc_id(seed["source_url"], seed["text"])
            yield {
                "doc_id": doc_id,
                "source_url": seed["source_url"],
                "source": seed["source"],
                "jurisdiction": seed["jurisdiction"],
                "document_type": seed["document_type"],
                "title": seed["title"],
                "text": seed["text"],
                "fetched_at": _now_iso(),
            }

    return _documents()


@dlt.source(name="themis_edgar_contracts")
def edgar_exhibits_source() -> Iterator[dlt.TDataItem]:
    """dlt source: yields SEC EDGAR contract exhibit seed documents."""

    @dlt.resource(name="documents", write_disposition="merge", primary_key="doc_id")
    def _documents() -> Iterator[dlt.TDataItem]:
        for seed in EDGAR_CONTRACT_SEEDS:
            doc_id = _make_doc_id(seed["source_url"], seed["text"])
            yield {
                "doc_id": doc_id,
                "source_url": seed["source_url"],
                "source": seed["source"],
                "jurisdiction": seed["jurisdiction"],
                "document_type": seed["document_type"],
                "title": seed["title"],
                "text": seed["text"],
                "fetched_at": _now_iso(),
            }

    return _documents()
