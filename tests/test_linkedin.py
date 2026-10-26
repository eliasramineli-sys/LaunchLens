import importlib.util
import json
from pathlib import Path
import urllib.error
import pytest

path = Path(__file__).resolve().parents[1] / 'scripts/publish_linkedin.py'
spec = importlib.util.spec_from_file_location('publisher', path)
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)


def release(assets=None):
    return {'id': 123, 'tag_name': 'v1.0.0', 'html_url': 'https://github.com/eliasramineli-sys/LaunchLens/releases/tag/v1.0.0', 'assets': assets or []}


def env(monkeypatch):
    monkeypatch.setenv('LINKEDIN_AUTHOR_URN', 'urn:li:person:example')
    monkeypatch.setenv('LINKEDIN_ACCESS_TOKEN', 'test-token-not-real')


def test_preview_content():
    template=(pub.ROOT/'social/linkedin_post.txt').read_text()
    text=pub.render_post(release(), 'eliasramineli-sys/LaunchLens', template)
    assert 'v1.0.0' in text and 'dados são sintéticos' in text.lower()
    assert len(text)<2800


def test_pending_before_send_and_success(monkeypatch):
    env(monkeypatch);events=[]
    def github(*args):
        state=json.loads(Path(args[3]).read_text())
        events.append(state['status'])
        assert 'test-token-not-real' not in json.dumps(state)
    def sender(*args):
        assert events==['pending']
        events.append('POST')
        return 'urn:li:share:123'
    result=pub.publish_release('eliasramineli-sys/LaunchLens',release(),'Texto',sender,github)
    assert events==['pending','POST','published']
    assert result.endswith('urn:li:share:123/')


def test_existing_record_blocks_all_network():
    def fail(*args):raise AssertionError('Não deve enviar')
    assert pub.publish_release('a/b',release([{'name':pub.STATE_NAME}]),'Texto',fail,fail)=='blocked_existing_record'


def test_timeout_keeps_pending_and_no_retry(monkeypatch):
    env(monkeypatch);states=[];calls=[]
    def github(*args):states.append(json.loads(Path(args[3]).read_text())['status'])
    def sender(*args):calls.append(1);raise RuntimeError('timeout')
    with pytest.raises(RuntimeError):pub.publish_release('a/b',release(),'Texto',sender,github)
    assert states==['pending'] and len(calls)==1


def test_reservation_failure_prevents_post(monkeypatch):
    env(monkeypatch)
    def github(*args):raise RuntimeError('permission denied')
    def sender(*args):raise AssertionError('Não deve enviar')
    with pytest.raises(RuntimeError):pub.publish_release('a/b',release(),'Texto',sender,github)


def test_missing_token_never_reserves(monkeypatch):
    monkeypatch.delenv('LINKEDIN_ACCESS_TOKEN', raising=False)
    monkeypatch.setenv('LINKEDIN_AUTHOR_URN', 'urn:li:person:example')
    def fail(*args):raise AssertionError('Não deve enviar')
    with pytest.raises(ValueError):pub.publish_release('a/b',release(),'Texto',fail,fail)


def test_http_401_redacts_response_and_token(monkeypatch):
    def error(*args,**kwargs):raise urllib.error.HTTPError('https://api.linkedin.com/rest/posts',401,'private response',{},None)
    monkeypatch.setattr(pub.urllib.request,'urlopen',error)
    with pytest.raises(RuntimeError) as e:pub.send_post('SECRET','urn:li:person:example','Texto','202610')
    assert '401' in str(e.value) and 'SECRET' not in str(e.value) and 'private response' not in str(e.value)


def test_payload_and_author():
    payload=pub.payload_for('urn:li:person:example','Texto')
    assert payload['visibility']=='PUBLIC' and payload['lifecycleState']=='PUBLISHED'
    with pytest.raises(ValueError):pub.payload_for('https://linkedin.com/in/test','Texto')


def test_preview_does_not_publish(monkeypatch,capsys):
    monkeypatch.setattr(pub.sys,'argv',['publisher','--tag','v1.0.0','--dry-run'])
    monkeypatch.setattr(pub,'release_metadata',lambda *a:release())
    def fail(*args):raise AssertionError('Não deve enviar')
    monkeypatch.setattr(pub,'publish_release',fail)
    pub.main()
    assert 'PRÉVIA' in capsys.readouterr().out
