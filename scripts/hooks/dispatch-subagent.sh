#!/usr/bin/env bash
# UserPromptSubmit hook: detect @-agent commands and inject a mandatory dispatch reminder
# for each DISTINCT agent mentioned. stdout is injected as a system reminder (treated as user
# feedback) before Claude responds. Exits 0 always — never blocks the message.
#
# Two refinements over a naive single-match: (1) ALL distinct @-mentions are handled, not just
# the first; (2) the three inline-only status reads that Alex handles in the main thread
# (@anja status, @kylie list, @sarah queue) are suppressed when that is the agent's only use,
# so they do not spuriously demand a sub-agent spawn.
set -uo pipefail

input="$(cat)"
msg="$(printf '%s' "$input" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("message",""))' 2>/dev/null || true)"
msg_lc="$(printf '%s' "$msg" | tr '[:upper:]' '[:lower:]')"

subagent_type() {
    case "$1" in
        anja)   echo "anja-ingest" ;;
        sarah)  echo "sarah-curator" ;;
        aaron)  echo "aaron-strategy" ;;
        adrian) echo "adrian-technical" ;;
        dana)   echo "dana-validator" ;;
        kylie)  echo "kylie-convert" ;;
    esac
}

# An agent's mention is suppressed only when it appears exactly once AND that once is its
# inline-only form; if it also appears in another context, we still emit (over-dispatch is
# safer than missing a required spawn).
agent_count() { printf '%s' "$msg_lc" | grep -oE "@$1\b" | wc -l | tr -d ' '; }
is_inline_only() {
    case "$1" in
        anja)  printf '%s' "$msg_lc" | grep -qE '@anja[[:space:]]+status' ;;
        kylie) printf '%s' "$msg_lc" | grep -qE '@kylie[[:space:]]+list' ;;
        sarah) printf '%s' "$msg_lc" | grep -qE '@sarah[[:space:]]+queue' ;;
        *)     return 1 ;;
    esac
}

agents="$(printf '%s' "$msg_lc" | grep -oE '@(anja|sarah|aaron|adrian|dana|kylie)' | tr -d '@' | sort -u || true)"

for agent in $agents; do
    if is_inline_only "$agent" && [ "$(agent_count "$agent")" = "1" ]; then
        continue
    fi
    sub="$(subagent_type "$agent")"
    printf 'DISPATCH REQUIRED: @%s detected. Spawn the %s sub-agent via the Agent tool immediately. Do NOT process this command in the main thread; the agent harness (checklist, Dana handoff, proposal queue) only runs inside the registered sub-agent profile.\n' "$agent" "$sub"
done

# Always-both rule (no exceptions): an @alex query must fan out to BOTH Aaron and Adrian.
# @alex is the main-thread orchestrator (there is no 'alex' sub-agent to spawn), so this is a
# distinct reminder from the loop above — it enforces the user's standing always-both preference
# even when the memory has fallen out of context.
if printf '%s' "$msg_lc" | grep -qE '@alex\b'; then
    printf 'DISPATCH REQUIRED: @alex query detected. Per the always-both rule (no exceptions), spawn BOTH aaron-strategy AND adrian-technical via the Agent tool, in parallel (both calls in one turn), before writing any substantive answer. Do NOT answer inline from wiki retrieval alone, even for a "quick" lookup or an in-context follow-up. Pre-fetch the candidate pages and pass them as prior_context so the agents do not re-fetch; synthesise only after both return.\n'
fi

exit 0
