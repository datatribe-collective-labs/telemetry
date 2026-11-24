def test_check_disk_passes_up_to_the_limit(hostcheck, disk):
    disk.percent = 85
    assert hostcheck.check_disk() == (85, [])


def test_check_disk_fails_over_the_limit(hostcheck, disk):
    disk.percent = 86
    used, problems = hostcheck.check_disk()
    assert used == 86
    assert problems == ["disk 86% used (limit 85%)"]
