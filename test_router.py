from router import route


def test_chat():
    assert route("What is DNS?") == ("chat", "What is DNS?")


def test_image_keyword():
    assert route("draw a cat")[0] == "image"
    assert route("Generate an image of a mountain")[0] == "image"


def test_image_command():
    assert route("/image a red car") == ("image", "a red car")


def test_say_command():
    assert route("/say hello everyone") == ("speech", "hello everyone")


def test_draw_inside_sentence_is_chat():
    assert route("How do I draw conclusions from data?")[0] == "chat"
