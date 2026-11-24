def test_env_value_returns_the_value_of_a_plain_line(hostcheck, tmp_path):
    (tmp_path / "repo/.env").write_text("# comment\nA=1\nHOSTCHECK_PING_URL=https://hc-ping.com/x\n")
    assert hostcheck.env_value("HOSTCHECK_PING_URL") == "https://hc-ping.com/x"


def test_env_value_ignores_malformed_lines_and_never_runs_them(hostcheck, tmp_path):
    (tmp_path / "repo/.env").write_text("> broken comment\nX=<a b>\nPUBLIC_HOSTNAME=demo.example\n")
    assert hostcheck.env_value("PUBLIC_HOSTNAME") == "demo.example"
    assert hostcheck.env_value("X") == "<a b>"  # returned as text, nothing is executed


def test_env_value_matches_the_whole_key_only(hostcheck, tmp_path):
    (tmp_path / "repo/.env").write_text("PUBLIC_HOSTNAME_OLD=old\n")
    assert hostcheck.env_value("PUBLIC_HOSTNAME") == ""


def test_env_value_is_empty_without_an_env_file(hostcheck):
    assert hostcheck.env_value("PUBLIC_HOSTNAME") == ""
