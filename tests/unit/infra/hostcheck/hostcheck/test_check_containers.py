import subprocess


def test_check_containers_passes_for_a_healthy_project(hostcheck, docker, make_container):
    docker.containers = [make_container("backend", health="healthy"), make_container("caddy"),
                         make_container("migrate", status="exited", exit_code=0)]
    assert hostcheck.check_containers() == []


def test_check_containers_only_looks_at_the_telemetry_project(hostcheck, docker, make_container):
    docker.containers = [make_container("backend")]
    hostcheck.check_containers()
    assert "label=com.docker.compose.project=telemetry" in docker.calls[0]


def test_check_containers_reports_a_stopped_service_once(hostcheck, docker, make_container):
    # A stopped container keeps its last health status: only "exited" is reported.
    docker.containers = [make_container("backend", status="exited", health="unhealthy")]
    assert hostcheck.check_containers() == ["backend is exited"]


def test_check_containers_reports_an_unhealthy_running_service(hostcheck, docker, make_container):
    docker.containers = [make_container("backend", health="unhealthy")]
    assert hostcheck.check_containers() == ["backend is unhealthy"]


def test_check_containers_reports_a_failed_one_shot_job(hostcheck, docker, make_container):
    docker.containers = [make_container("migrate", status="exited", exit_code=1),
                         make_container("airflow-init", status="exited", exit_code=0)]
    assert hostcheck.check_containers() == ["migrate exited with code 1"]


def test_check_containers_reports_an_out_of_memory_kill(hostcheck, docker, make_container):
    docker.containers = [make_container("dashboard", oom=True)]
    assert hostcheck.check_containers() == ["dashboard was killed: out of memory"]


def test_check_containers_reports_restarts_since_the_last_check(hostcheck, docker, make_container):
    docker.containers = [make_container("physics_models", restarts=1)]
    assert hostcheck.check_containers() == []  # first sight: the baseline
    docker.containers = [make_container("physics_models", restarts=3)]
    assert hostcheck.check_containers() == ["physics_models restarted 2x since the last check"]
    assert hostcheck.check_containers() == []  # no new restarts since


def test_check_containers_starts_over_for_a_recreated_container(hostcheck, docker, make_container):
    docker.containers = [make_container("backend", restarts=5, cid="old")]
    hostcheck.check_containers()
    docker.containers = [make_container("backend", restarts=6, cid="new")]  # a deploy: new id
    assert hostcheck.check_containers() == []


def test_check_containers_reports_docker_not_answering(hostcheck, docker):
    docker.error = subprocess.TimeoutExpired(["docker", "ps"], 10)
    (problem,) = hostcheck.check_containers()
    assert problem.startswith("docker check failed: TimeoutExpired")


def test_check_containers_reports_a_missing_docker(hostcheck, docker):
    docker.error = FileNotFoundError("docker")
    (problem,) = hostcheck.check_containers()
    assert problem.startswith("docker check failed: FileNotFoundError")


def test_check_containers_reports_an_empty_project(hostcheck, docker):
    assert hostcheck.check_containers() == ["no containers found for compose project 'telemetry'"]
