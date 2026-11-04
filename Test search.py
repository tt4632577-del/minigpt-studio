from search import should_search


def test_factual_questions_trigger_search():
    assert should_search("Who is the dean of the School of Information Science at Presidency University?")
    assert should_search("latest cricket score")
    assert should_search("What is the admission deadline for MCA?")


def test_general_questions_skip_search():
    assert not should_search("hi")
    assert not should_search("Explain recursion with an example")
    assert not should_search("Write a Python function to reverse a string")