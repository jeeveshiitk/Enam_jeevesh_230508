from app.research import validate_claims, retrieve
from app.providers import document_links, directory_filings


EVIDENCE = [dict(id='D1P1C0', text='Management expects revenue growth of ten percent in the next year.', title='Call', kind='transcript', page=1, url='https://company.test/call.pdf')]


def test_fabricated_citation_and_quote_are_rejected():
    cards, _ = validate_claims({'cards': [
        {'heading':'valid', 'evidence':[{'id':'D1P1C0','quote':'expects revenue growth of ten percent'}]},
        {'heading':'fake id', 'evidence':[{'id':'D9','quote':'expects revenue growth of ten percent'}]},
        {'heading':'fake quote', 'evidence':[{'id':'D1P1C0','quote':'expects revenue growth of fifty percent'}]},
    ]}, EVIDENCE)
    assert [c['heading'] for c in cards] == ['valid']


def test_single_source_is_not_a_promised_delivered_pair():
    _, pairs = validate_claims({'comparisons':[{'period':'Q1','evidence':[{'id':'D1P1C0','quote':'expects revenue growth of ten percent'}]}]}, EVIDENCE)
    assert pairs == []


def test_comparison_requires_named_metric_and_two_documents():
    evidence = EVIDENCE + [dict(id='D2P1C0', text='Reported revenue growth for the year was ten percent.', title='Later call', kind='transcript', page=1, url='https://company.test/later.pdf')]
    row = {'metric':'Revenue growth','basis':'Annual percentage growth','period':'FY26','promised':'10%','delivered':'10%','verdict':'Met','evidence':[{'id':'D1P1C0','quote':'expects revenue growth of ten percent'},{'id':'D2P1C0','quote':'Reported revenue growth for the year was ten percent.'}]}
    assert len(validate_claims({'comparisons':[row]}, evidence)[1]) == 1
    del row['metric']
    assert validate_claims({'comparisons':[row]}, evidence)[1] == []


def test_document_discovery_excludes_summaries_and_recordings():
    html = '''<div class="documents"><h3>Annual reports</h3><ul><li><a href="https://company.test/ar.pdf">Annual Report 2026</a></li></ul></div>
    <div class="documents"><div><h3>Concalls</h3></div><ul><li>Jul 2026<a href="https://company.test/transcript.pdf">Transcript</a><a href="https://company.test/summary">AI Summary</a><a href="https://company.test/audio.mp3">REC</a></li></ul></div>'''
    docs = document_links(html)
    assert len(docs) == 2
    assert {d['kind'] for d in docs} == {'annual_report','transcript'}
    assert docs[1]['url'].endswith('transcript.pdf')


def test_missing_filing_date_is_not_fabricated():
    assert directory_filings('TEST', '<section id="documents"><a href="https://www.bseindia.com/a.pdf">Annual report</a></section>') == []


def test_retrieval_keeps_each_document_represented():
    documents = [{'kind':'annual_report','title':'Report','url':'https://company.test/a.pdf','pages':[{'page':1,'text':'revenue growth guidance '*500}]}, {'kind':'transcript','title':'Call','url':'https://company.test/c.pdf','pages':[{'page':2,'text':'management guidance expects growth next quarter '*10}]}]
    evidence = retrieve(documents, 'promises')
    assert {e['kind'] for e in evidence} == {'annual_report','transcript'}
