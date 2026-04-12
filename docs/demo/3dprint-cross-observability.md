# 3dprint Cross-Observability Demo Script

This script is written for a mixed audience:

- Splunk SEs
- Solution Architects
- Executives

Assume not everyone in the room understands networking. Explain in plain English first, then use the tooling to prove the point.

## Demo Outcome

By the end of the demo, the audience should understand three things:

1. A public app can look healthy at the front door while a business workflow is still broken.
2. Different tools answer different questions because they observe from different vantage points.
3. Splunk RUM, ThousandEyes, Splunk Observability Cloud, Network Explorer, and Isovalent fit together instead of competing with each other.

## Story in Plain English

The app is a manufacturing workflow called FilaOps.

The normal user story is simple:

1. A staff user logs in.
2. They go to the order import page.
3. They upload a CSV.
4. The frontend calls the backend.
5. The backend hands parsing work to `order-ingest`.
6. The import completes.

The demo break is also simple:

1. The website stays up.
2. Login still works.
3. Navigation still works.
4. A temporary network policy blocks one internal handoff: `backend -> order-ingest`.
5. The CSV import fails even though the public site still looks healthy.

This is the whole point of the demo:

- availability is not the same thing as business success
- front-door monitoring is not the same thing as workflow monitoring
- network visibility is not the same thing as user-experience visibility

## Tool Roles

Use this framing early so the audience has a mental map:

- Splunk RUM answers: "What are real users experiencing in the browser?"
- ThousandEyes answers: "How does the app look from outside-in or from another vantage point?"
- Splunk APM and Service Map answer: "Which service dependency is slow or failing?"
- Splunk Network Explorer answers: "Which service edge or network relationship is impacted inside the environment?"
- Isovalent answers: "What network policy or flow decision caused that impact?"

## ThousandEyes Vantage Points

For this demo, use ThousandEyes account group `2114135`, which is labeled `Splunk Observability Demo`.

When you say "vantage point," explain it like this:

> A vantage point is simply where we are standing when we test the application.

That matters because the answer changes depending on where you stand.

### Outside-In Vantage

This is the view from the internet or from remote users.

- It tells you whether people can reach the app.
- It tells you how the path to the app behaves.
- It helps you separate "the site is unreachable" from "the site is reachable but something deeper is wrong."

In ThousandEyes, this usually comes from Cloud Agents.

### Inside-the-Environment Vantage

This is the view from a private or enterprise location closer to where workloads run.

- It helps you validate app behavior from an internal office, branch, or private environment.
- It is useful when users, APIs, or dependencies live on private paths that the public internet cannot see.

In ThousandEyes, this usually comes from Enterprise Agents.

### Why Call This Out in the Demo

The audience does not need to remember product names. They need to remember the business meaning:

- outside-in tells us whether customers can get in
- inside-the-environment tells us whether internal paths and business logic still work

## Why We Chose These ThousandEyes Tests

The repo provisions three ThousandEyes tests:

- `FilaOps Demo - Frontend HTTP`
- `FilaOps Demo - Admin Browser`
- `FilaOps Demo - Admin API`

Each one exists for a different reason.

### 1. HTTP Server Test

What it proves:

- the public entry point is reachable
- the server is returning the expected status
- network and BGP measurements stay attached to the public URL

Why we chose it:

- it is the cleanest "is the front door open?" test
- executives understand this immediately
- it gives us a stable baseline that stays healthy during the demo break

Presenter line:

> This is our simplest availability check. If this is green, the front door is open.

### 2. Browser Transaction Test

What it proves:

- the login page loads
- a real browser can sign in
- the app can render and navigate to the order import page

Why we chose it:

- it makes the story human
- it is much easier for a mixed audience to relate to a login journey than a raw latency chart
- it shows rendered experience, not just endpoint health

Important callout:

This browser test does not prove the whole CSV import workflow. It proves the user can get into the experience and reach the right page.

Presenter line:

> This tells us the application experience is reachable and usable as far as a person would see it in the browser.

### 3. API Test

What it proves:

- authentication works through the API
- the backend can serve authenticated requests
- we can test an application path without browser rendering noise

Why we chose it:

- it isolates app behavior from browser rendering behavior
- it helps us separate "the page is slow" from "the workflow API is unhealthy"
- it is the best synthetic check for the authenticated admin path in this demo

Presenter line:

> This is our clean app-path check. It removes browser rendering from the conversation and tests the authenticated workflow path directly.

## Why These Three Tests Together Matter

One test alone would make the story weak.

Together they let us say:

- the front door is open
- the browser experience is reachable
- the authenticated app path is behaving differently depending on what is broken

That is exactly what we need for this demo, because the break is internal, not public.

## Prerequisites

### Turnkey path (recommended)

From a bare Kubernetes cluster with `kubectl`, `helm`, `curl`, and `jq` available:

```sh
cp scripts/demo/.env.example scripts/demo/.env.local
# Fill in: SPLUNK_REALM, SPLUNK_ACCESS_TOKEN, THOUSANDEYES_BEARER_TOKEN,
#          FRONTEND_URL, DEMO_ADMIN_EMAIL, DEMO_ADMIN_PASSWORD

bash scripts/demo/3dprint-observability.sh deploy
```

This single command installs the OTel collector, deploys the app, provisions
ThousandEyes tests (with both metric and trace streams), auto-detects Cilium
and configures Hubble metrics scraping, and creates Splunk dashboards with
trace correlation panels. When it finishes, it prints all dashboard links.

### Manual path

If you already have the app deployed and the OTel collector running, you can
provision only the observability integrations:

```sh
cp scripts/demo/.env.example scripts/demo/.env.local
# fill in credentials
bash scripts/demo/3dprint-observability.sh setup
```

See `scripts/demo/.env.example` for the full list of required and optional
environment variables. If the ThousandEyes account group is quota-locked for
browser/API tests, pin the existing shared transaction-test IDs with
`THOUSANDEYES_PIN_EXISTING_TRANSACTION_TESTS=true`. If those shared IDs do not
actually point at the FilaOps demo URLs, the setup skips the imported generic
ThousandEyes package dashboards and keeps the custom FilaOps dashboards only.
If `ISOVALENT_DASHBOARD_URL` is left blank, the setup tries to auto-discover
the built-in `Cilium by Isovalent` and `Hubble by Isovalent` dashboards in the
Splunk Observability org and uses those links in the demo notes when available.

## Operator Commands

Run the clean baseline:

```sh
bash scripts/demo/3dprint-observability.sh baseline
```

Introduce the reversible failure:

```sh
bash scripts/demo/3dprint-observability.sh break
```

Restore the app:

```sh
bash scripts/demo/3dprint-observability.sh restore
```

Print the current dashboard and handoff links:

```sh
bash scripts/demo/3dprint-observability.sh links
```

Remove the demo policy and finished jobs:

```sh
bash scripts/demo/3dprint-observability.sh cleanup
```

To also delete the repo-managed ThousandEyes and Splunk objects recorded in local state:

```sh
PURGE_REMOTE_ASSETS=true bash scripts/demo/3dprint-observability.sh cleanup
```

## Presenter Flow

### 1. Frame the Problem

What to say:

> I want to show the difference between a site being reachable and a business workflow being healthy. We are going to keep the app up, keep login working, and break one internal handoff so we can watch each tool explain a different part of the same problem.

### 2. Start in Splunk Observability Cloud

Open:

- `FilaOps Demo - App + ThousandEyes`

What to show:

- the note tile with links
- the ThousandEyes availability and completion signals
- the backend order-import latency and 502 charts

What to say:

> We start in one operational view. ThousandEyes is giving us outside-in and synthetic checks. Splunk is showing us the application and service behavior beside those checks.

### 3. Explain the Three ThousandEyes Tests

Stay on the app dashboard, then move into the imported ThousandEyes package dashboards.

What to say:

> We deliberately chose three tests because each answers a different question. HTTP tells us if the front door is open. The browser transaction tells us a person can reach and use the login journey. The API test tells us whether the authenticated application path is healthy without depending on browser rendering.

Call out the vantage point:

> Where these tests run from matters. If I run them from a public cloud vantage point, I am seeing what an outside user sees. If I run them from an enterprise or private vantage point, I am seeing what an internal location sees.

### 4. Show the Healthy Baseline

Run:

```sh
bash scripts/demo/3dprint-observability.sh baseline
```

What to show:

- baseline dashboard signals are healthy
- login/browser flow completes
- API flow completes
- order import succeeds

What to say:

> This is the clean state. The front door works, the browser journey works, and the internal business workflow works.

### 5. Introduce the Break

Run:

```sh
bash scripts/demo/3dprint-observability.sh break
```

What the script does:

- applies a reversible deny policy
- blocks `backend -> order-ingest`
- reruns the focused order-import smoke and expects `502`

What to say:

> I am not taking the website down. I am only blocking one internal dependency. This is what makes the demo useful: the public app can still look fine while the workflow is now broken.

### 6. Return to Splunk O11y

What to show:

- ThousandEyes HTTP stays green
- ThousandEyes browser transaction can still show the app is reachable
- backend order-import 502s appear
- backend order-import latency changes
- event markers line up with the break

What to say:

> This is the key learning moment. The front door is still healthy. That does not mean the business transaction is healthy.

### 7. Open Service Map and Network Explorer

What to show:

- Service Map for the app services
- Network Explorer filtered to namespace `3dprint`
- focus on the `filaops-backend` to `filaops-order-ingest` relationship

What to say:

> Service Map tells us which dependency is part of the failing path. Network Explorer tells us this is not just a code problem, it is also a relationship problem between services.

Plain-English translation:

- Service Map = who talks to whom in the app
- Network Explorer = which network relationship is active, degraded, or affected

### 8. Open Isovalent

What to show:

- the deny policy
- the denied flow
- the impacted edge

What to say:

> Isovalent is the deep proof. Splunk told us where to look. Isovalent shows the exact policy decision and flow behavior behind the failure.

### 9. Restore the App

Run:

```sh
bash scripts/demo/3dprint-observability.sh restore
```

What to show:

- order import succeeds again
- 502s stop
- app path recovers without redeploying the app

What to say:

> We did not redeploy. We removed the policy and the workflow recovered. That confirms the issue was dependency-level and policy-driven, not a random app restart artifact.

## Audience Callouts

### For Executives

Say this clearly:

- healthy homepage does not guarantee healthy revenue path
- faster root cause understanding reduces time spent blaming the wrong team
- multiple vantage points reduce business ambiguity during incidents

### For SEs

Call out:

- RUM is real-user telemetry
- ThousandEyes is synthetic outside-in and cross-vantage validation
- APM and Service Map show service dependencies
- Network Explorer and Isovalent narrow the problem from "something is slow" to "this edge or policy is the reason"

### For Solution Architects

Call out:

- the demo keeps each tool in its proper role
- the same incident can look different at browser, edge, service, and policy layers
- the value is in correlation, not in forcing one tool to do every job

## Simple Networking Translation

Use these phrases if the room starts to drift into jargon:

- "path" means the route traffic takes from one point to another
- "packet loss" means some traffic never arrives
- "latency" means traffic arrives, but more slowly than expected
- "policy deny" means a rule intentionally blocked communication
- "service edge" means one service talking to another service
- "synthetic monitoring" means we are testing on purpose, not waiting for a real user to report pain

## What Not to Overclaim

- ThousandEyes is not replacing RUM. It is giving synthetic and vantage-based perspective.
- RUM is not replacing ThousandEyes. It is giving real-user browser evidence.
- Service Map and Network Explorer do not replace Isovalent. They narrow the blast radius and help you know where to drill in.
- Isovalent is not the user experience tool. It is the deep network and policy truth source for this scenario.

## Repo-Specific Notes

- The live failure used in this demo is `backend -> order-ingest` on `8030/TCP`.
- If the cluster exposes `ciliumnetworkpolicies.cilium.io`, the wrapper uses `k8s/3dprint/policies/order-ingest-deny.cnp.yaml`.
- If the Cilium CRD is absent, the wrapper falls back to `k8s/3dprint/policies/order-ingest-deny.netpol.yaml`, which is broader: it blocks **all** ingress to `order-ingest`, not just traffic from the backend. Direct health probes to `order-ingest` will also fail while the policy is applied on non-Cilium clusters. The demo break/restore sequence remains correct because the smoke test routes through the backend, but avoid running `baseline` (which health-checks `order-ingest` directly) while the policy is active on a non-Cilium cluster.
- The browser transaction proves login and navigation to the order-import page.
- The focused order-import failure is asserted by the in-cluster backend smoke flow during the break.
- The `deploy` command auto-detects Cilium and configures the Splunk OTel Collector to scrape Hubble metrics (`cilium_drop_count_total`, `hubble_flows_processed_total`). The Policy Impact dashboard uses these metrics directly.
- If Hubble metrics are not available, the policy-impact dashboard shows a no-data message with instructions; use Network Explorer plus the Isovalent handoff instead.
- ThousandEyes sends both metrics and traces to Splunk Observability via two OpenTelemetry streams. The "App + ThousandEyes" dashboard includes trace correlation panels that overlay TE synthetic latency with backend OTel latency and link to the APM service map.
- The backend returns `Server-Timing: traceparent` headers (`SPLUNK_TRACE_RESPONSE_HEADER_ENABLED=true`), enabling browser-to-backend trace correlation in Splunk RUM and ThousandEyes browser tests.
