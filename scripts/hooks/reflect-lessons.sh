#!/usr/bin/env bash
# UserPromptSubmit hook: detect that the user may be correcting a prior answer (or restating a
# standing preference) and inject a NON-BLOCKING nudge for Alex to consider capturing a durable
# lesson. stdout is injected as a system reminder (treated as user feedback) before Claude responds.
# Exits 0 always — never blocks the message.
#
# The hook does NO reasoning about what the lesson is; it only raises the possibility. Alex decides
# whether a generalisable lesson applies and, if so, drafts a Lesson-capture proposal via the
# @alex learn procedure (still pending, still human-approved). False positives are harmless: Alex
# judges there is no durable lesson and simply answers.
set -uo pipefail

input="$(cat)"
msg="$(printf '%s' "$input" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("message",""))' 2>/dev/null || true)"
msg_lc="$(printf '%s' "$msg" | tr '[:upper:]' '[:lower:]')"

# Correction / preference-restatement signals. Deliberately phrase-based (not bare single words)
# to limit false positives. A hit only raises a nudge; it never blocks.
signals="that'?s (wrong|incorrect|not right|not correct)|that is (wrong|incorrect|not right|not correct)"
signals="$signals|you'?re wrong|you are wrong|you got (that|it) wrong|that'?s not (right|correct)"
signals="$signals|not correct|should (be|have been)|^actually[, ]|actually,|^no[,.]|correction:"
signals="$signals|not what i (said|meant|asked)|from now on|always (do|use|prefer)|never (do|use)|i prefer"

if printf '%s' "$msg_lc" | grep -qE "$signals"; then
    printf 'POSSIBLE CORRECTION: the user may be correcting a prior answer or restating a standing preference. If a durable, generalisable lesson applies (not a one-off), draft a Lesson-capture proposal via the @alex learn procedure (wiki/agents/alex-master.md -> Learning loop): a pending row in wiki/pending/update-proposals.md targeting the relevant wiki/agents/lessons/<agent>.md or wiki/profile/engagement.md, for approval via @sarah approve-all. If there is no generalisable lesson, ignore this and just answer.\n'
fi

exit 0
