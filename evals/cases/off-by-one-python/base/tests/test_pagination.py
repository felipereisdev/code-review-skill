from reports.pagination import paginate


def test_first_page():
    page = paginate(list(range(25)), page=1)
    assert page.items == list(range(10))
    assert page.total_pages == 3
