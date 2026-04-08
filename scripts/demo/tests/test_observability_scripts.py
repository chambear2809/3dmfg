import json
import os
import subprocess
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _demo_env(tmp_path: Path) -> dict[str, str]:
    return {
        "DEMO_STATE_DIR": str(tmp_path),
        "DEMO_STATE_FILE": str(tmp_path / "state.json"),
        "FRONTEND_URL": "https://demo.example.com",
        "PUBLIC_API_BASE_URL": "https://demo.example.com/api/v1",
        "THOUSANDEYES_ACCOUNT_GROUP_ID": "2114135",
        "THOUSANDEYES_API_TOKEN": "test-thousandeyes-token",
        "SPLUNK_O11Y_API_TOKEN": "test-splunk-token",
        "SPLUNK_O11Y_REALM": "us1",
    }


def _run_bash(script: str, env: dict[str, str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["bash", "-lc", textwrap.dedent(script)],
        cwd=REPO_ROOT,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"bash exited with {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def _load_state(env: dict[str, str]) -> dict:
    return json.loads(Path(env["DEMO_STATE_FILE"]).read_text())


class TestThousandEyesBindingValidation:
    def test_marks_vendor_dashboards_unsupported_for_mismatched_pinned_tests(self, tmp_path):
        env = _demo_env(tmp_path)

        result = _run_bash(
            """
            source scripts/demo/lib/common.sh
            source scripts/demo/lib/thousandeyes.sh

            state_set_string "thousandeyes.tests.http_server.id" "8436273"
            state_set_string "thousandeyes.tests.web_transaction.id" "8263826"
            state_set_string "thousandeyes.tests.api.id" "8260502"

            te_request() {
              local method="$1"
              local path="$2"

              case "${path}" in
                "/tests/http-server/8436273?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}")
                  printf '%s' '{"testName":"FilaOps Demo - Frontend HTTP","url":"https://demo.example.com/"}'
                  ;;
                "/tests/web-transactions/8263826?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}")
                  printf '%s' '{"testName":"aleccham-broadcast-browser","url":"https://broadcast.example.com/broadcast.html"}'
                  ;;
                "/tests/api/8260502?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}")
                  printf '%s' '{"testName":"aleccham-broadcast-demo-monkey","url":"https://streaming.example.internal/api/v1/demo/public/trace-map"}'
                  ;;
                *)
                  printf 'unexpected path: %s\\n' "${path}" >&2
                  return 1
                  ;;
              esac
            }

            te_refresh_demo_test_bindings >/dev/null || true
            """,
            env,
        )

        state = _load_state(env)
        tests = state["thousandeyes"]["tests"]

        assert state["thousandeyes"]["vendor_dashboards_supported"] == "false"
        assert tests["http_server"]["compatible"] == "true"
        assert tests["web_transaction"]["compatible"] == "false"
        assert tests["api"]["compatible"] == "false"
        assert tests["web_transaction"]["resolved_name"] == "aleccham-broadcast-browser"
        assert tests["api"]["resolved_url"] == "https://streaming.example.internal/api/v1/demo/public/trace-map"
        assert "related dashboards will be skipped" in result.stderr

    def test_accepts_shared_tests_when_urls_match_demo_prefixes(self, tmp_path):
        env = _demo_env(tmp_path)

        _run_bash(
            """
            source scripts/demo/lib/common.sh
            source scripts/demo/lib/thousandeyes.sh

            state_set_string "thousandeyes.tests.http_server.id" "8436273"
            state_set_string "thousandeyes.tests.web_transaction.id" "8263826"
            state_set_string "thousandeyes.tests.api.id" "8260502"

            te_request() {
              local method="$1"
              local path="$2"

              case "${path}" in
                "/tests/http-server/8436273?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}")
                  printf '%s' '{"testName":"shared-http-check","url":"https://demo.example.com/"}'
                  ;;
                "/tests/web-transactions/8263826?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}")
                  printf '%s' '{"testName":"shared-browser-check","url":"https://demo.example.com/admin/login"}'
                  ;;
                "/tests/api/8260502?aid=${THOUSANDEYES_ACCOUNT_GROUP_ID}")
                  printf '%s' '{"testName":"shared-api-check","url":"https://demo.example.com/api/v1/auth/login"}'
                  ;;
                *)
                  printf 'unexpected path: %s\\n' "${path}" >&2
                  return 1
                  ;;
              esac
            }

            te_refresh_demo_test_bindings >/dev/null
            """,
            env,
        )

        state = _load_state(env)
        tests = state["thousandeyes"]["tests"]

        assert state["thousandeyes"]["vendor_dashboards_supported"] == "true"
        assert tests["http_server"]["compatible"] == "true"
        assert tests["web_transaction"]["compatible"] == "true"
        assert tests["api"]["compatible"] == "true"
        assert tests["web_transaction"]["resolved_url"] == "https://demo.example.com/admin/login"
        assert tests["api"]["resolved_url"] == "https://demo.example.com/api/v1/auth/login"


class TestSplunkDashboardCleanup:
    def test_prunes_only_the_blank_placeholder_dashboard(self, tmp_path):
        env = _demo_env(tmp_path)
        env["DELETE_LOG"] = str(tmp_path / "deletes.log")

        _run_bash(
            """
            source scripts/demo/lib/common.sh
            source scripts/demo/lib/splunk_o11y.sh

            : > "${DELETE_LOG}"

            sfx_request() {
              local method="$1"
              local path="$2"

              case "${path}" in
                "/v2/dashboardgroup/GROUP1")
                  printf '%s' '{"dashboards":["EMPTY","REAL","OTHEREMPTY"]}'
                  ;;
                "/v2/dashboard/EMPTY")
                  printf '%s' '{"name":"FilaOps Cross-Observability Demo","charts":[]}'
                  ;;
                "/v2/dashboard/REAL")
                  printf '%s' '{"name":"FilaOps Demo - App + ThousandEyes","charts":[{"chartId":"chart-1"}]}'
                  ;;
                "/v2/dashboard/OTHEREMPTY")
                  printf '%s' '{"name":"Some Other Dashboard","charts":[]}'
                  ;;
                *)
                  printf 'unexpected path: %s\\n' "${path}" >&2
                  return 1
                  ;;
              esac
            }

            sfx_delete() {
              printf '%s\\n' "$1" >> "${DELETE_LOG}"
            }

            sfx_prune_empty_group_dashboards "GROUP1" "FilaOps Cross-Observability Demo"
            """,
            env,
        )

        deleted = Path(env["DELETE_LOG"]).read_text().splitlines()
        assert deleted == ["/v2/dashboard/EMPTY"]

    def test_cleanup_dashboard_package_deletes_assets_and_clears_state(self, tmp_path):
        env = _demo_env(tmp_path)
        env["DELETE_LOG"] = str(tmp_path / "deletes.log")

        _run_bash(
            """
            source scripts/demo/lib/common.sh
            source scripts/demo/lib/splunk_o11y.sh

            : > "${DELETE_LOG}"

            state_set_string "splunk.packages.vendor_te.dashboards.application" "DASH-1"
            state_set_string "splunk.packages.vendor_te.dashboards.network" "DASH-2"
            state_set_string "splunk.packages.vendor_te.charts.one" "CHART-1"
            state_set_string "splunk.packages.vendor_te.charts.two" "CHART-2"
            state_set_string "splunk.packages.vendor_te.group_id" "GROUP-1"

            sfx_delete() {
              printf '%s\\n' "$1" >> "${DELETE_LOG}"
            }

            sfx_cleanup_dashboard_package "splunk.packages.vendor_te"
            """,
            env,
        )

        deleted = set(Path(env["DELETE_LOG"]).read_text().splitlines())
        state = _load_state(env)

        assert deleted == {
            "/v2/dashboard/DASH-1",
            "/v2/dashboard/DASH-2",
            "/v2/chart/CHART-1",
            "/v2/chart/CHART-2",
            "/v2/dashboardgroup/GROUP-1",
        }
        assert state.get("splunk", {}).get("packages", {}) == {}


class TestIsovalentLinkDiscovery:
    def test_caches_builtin_cilium_and_hubble_dashboard_links(self, tmp_path):
        env = _demo_env(tmp_path)

        _run_bash(
            """
            source scripts/demo/lib/common.sh
            source scripts/demo/lib/splunk_o11y.sh

            sfx_request() {
              local method="$1"
              local path="$2"

              case "${path}" in
                "/v2/dashboardgroup?limit=200")
                  printf '%s' '{"results":[{"id":"CILIUM-GROUP","name":"Cilium by Isovalent"},{"id":"HUBBLE-GROUP","name":"Hubble by Isovalent"}]}'
                  ;;
                "/v2/dashboardgroup/CILIUM-GROUP")
                  printf '%s' '{"dashboards":["CILIUM-1","CILIUM-2"]}'
                  ;;
                "/v2/dashboardgroup/HUBBLE-GROUP")
                  printf '%s' '{"dashboards":["HUBBLE-1","HUBBLE-2"]}'
                  ;;
                "/v2/dashboard/CILIUM-1")
                  printf '%s' '{"name":"High-Level Health","charts":[{"chartId":"x"}]}'
                  ;;
                "/v2/dashboard/CILIUM-2")
                  printf '%s' '{"name":"Policy Verdicts","charts":[{"chartId":"x"}]}'
                  ;;
                "/v2/dashboard/HUBBLE-1")
                  printf '%s' '{"name":"DNS Overview","charts":[{"chartId":"x"}]}'
                  ;;
                "/v2/dashboard/HUBBLE-2")
                  printf '%s' '{"name":"Network Overview","charts":[{"chartId":"x"}]}'
                  ;;
                *)
                  printf 'unexpected path: %s\\n' "${path}" >&2
                  return 1
                  ;;
              esac
            }

            sfx_cache_isovalent_dashboard_links
            """,
            env,
        )

        state = _load_state(env)
        urls = state["splunk"]["isovalent"]["dashboard_urls"]

        assert urls["cilium_policy_verdicts"] == "https://app.us1.signalfx.com/#/dashboard/CILIUM-2"
        assert urls["hubble_network_overview"] == "https://app.us1.signalfx.com/#/dashboard/HUBBLE-2"

    def test_demo_note_uses_discovered_isovalent_links_when_env_var_is_unset(self, tmp_path):
        env = _demo_env(tmp_path)

        result = _run_bash(
            """
            source scripts/demo/lib/common.sh
            source scripts/demo/lib/splunk_o11y.sh

            state_set_string "splunk.isovalent.dashboard_urls.cilium_policy_verdicts" "https://app.us1.signalfx.com/#/dashboard/CILIUM-2"
            state_set_string "splunk.isovalent.dashboard_urls.hubble_network_overview" "https://app.us1.signalfx.com/#/dashboard/HUBBLE-2"

            sfx_demo_note_markdown "demo-20260408010101"
            """,
            env,
        )

        assert "[open Cilium Policy Verdicts](https://app.us1.signalfx.com/#/dashboard/CILIUM-2)" in result.stdout
        assert "[open Hubble Network Overview](https://app.us1.signalfx.com/#/dashboard/HUBBLE-2)" in result.stdout
