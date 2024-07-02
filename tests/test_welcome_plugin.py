def test_handle_team_join():
    user_id = "D0730R9KFC2"
    with open("welcome_message.txt", "r", encoding="utf-8") as file:
        welcome_message_template = file.read()

    welcome_message = welcome_message_template.format(user_id=user_id)

    expected_message = (
        ":tada: *Welcome to the OWASP Slack Community, <@D0730R9KFC2>!* :tada:\n\n"
        "We're thrilled to have you here! Whether you're new to OWASP or a long-time contributor, "
        "this Slack workspace is the perfect place to connect, collaborate, and stay informed "
        "about all things OWASP.\n\n"
        ":small_blue_diamond: *Get Involved:*\n"
        "• Check out the *#contribute* channel to find ways to get involved with OWASP"
        " projects and initiatives.\n"
        "• Explore individual project channels, which are named *#project-name*,"
        " to dive into specific projects that interest you.\n"
        "• Join our chapter channels, named *#chapter-name*, to connect with "
        "local OWASP members in your area.\n\n"
        ":small_blue_diamond: *Stay Updated:*\n"
        "• Visit *#newsroom* for the latest updates and announcements.\n"
        "• Follow *#external-activities* for news about OWASP's engagement "
        "with the wider security community.\n\n"
        ":small_blue_diamond: *Connect and Learn:*\n"
        "• *#jobs*: Looking for new opportunities? Check out the latest job postings here.\n"
        "• *#leaders*: Connect with OWASP leaders and stay informed about leadership activities.\n"
        "• *#project-committee*: Engage with the committee overseeing OWASP projects.\n"
        "• *#gsoc*: Stay updated on Google Summer of Code initiatives.\n"
        "• *#github-admins*: Get support and discuss issues "
        "related to OWASP's GitHub repositories.\n"
        "• *#learning*: Share and find resources to expand your knowledge "
        "in the field of application security.\n\n"
        "We're excited to see the amazing contributions you'll make. "
        "If you have any questions or need assistance, don't hesitate to ask. "
        "Let's work together to make software security visible and improve the"
        " security of the software we all rely on.\n\n"
        "Welcome aboard! :rocket:"
    )

    assert welcome_message.strip() == expected_message.strip()
