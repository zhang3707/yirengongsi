"""T-113c: mock 数据在报告中的警示标注"""

from skill_runtime.builtin.report import _mock_report


def test_mock_report_includes_mock_warning():
    sources = [{"title": "Mock商品", "origin": "mock", "url": "https://mock.example.com/1"}]
    content = _mock_report("模拟数据报告", ["发现1"], [], sources)
    assert "模拟数据" in content
    assert "⚠️" in content


def test_real_report_has_no_mock_warning():
    sources = [{"title": "真实商品", "origin": "taobao", "url": "https://item.taobao.com/1"}]
    content = _mock_report("真实数据报告", ["发现1"], [], sources)
    assert "模拟数据" not in content
