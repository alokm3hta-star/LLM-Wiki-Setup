# n8n integration: WhatsApp to Ask Alex

A reference [n8n](https://n8n.io) workflow that lets you query the wiki from WhatsApp: send a message, get a grounded, cited answer back from Alex. This is the build described in Part 4 of the blog series.

> **This is a sanitised template.** Every secret and machine-specific value has been replaced with a placeholder (`YOUR_PHONE_NUMBER_ID`, `REPLACE_WITH_YOUR_*_CREDENTIAL_ID`, and the paths in the SSH command). Fill them in locally and never commit your real IDs, tokens, paths, or keychain password file.

## How it works

n8n cannot run the wiki engine directly, so it reaches the machine where the wiki and Claude Code live over **SSH** and runs Claude Code **headless** (`claude -p "@alex ask ..."`), which boots the constitution and all the guardrails.

```
WhatsApp message
  -> POST webhook
  -> Fetch Sender        (parse the text and the sender)
  -> "Working, please wait..."   (WhatsApp send, so there is no silence)
  -> Call Alex           (SSH: unlock keychain, then claude -p "@alex ask ...")
  -> Prep Response       (extract the answer between <<<A>>> and <<<Z>>>)
  -> Reply               (WhatsApp send)
```

A separate **GET** webhook wired to a **Respond to Webhook** node handles Meta's verification by echoing `hub.challenge` (see gotcha 1).

## Prerequisites

- A self-hosted n8n instance.
- A host running the wiki and Claude Code (signed in), with Remote Login (SSH) enabled, kept powered on and logged in.
- A Meta WhatsApp Cloud API app with a WhatsApp Business Account (WABA).
- A public HTTPS endpoint for the webhook (for example a Cloudflare Tunnel to your n8n).

## Setup

1. Import `ask-alex.workflow.json` into n8n.
2. Replace the placeholders:
   - **Call Alex (SSH node):** attach your SSH credential, and in the command replace `/path/to/your/keychain-password-file`, `/Users/YOU/Library/Keychains/login.keychain-db`, `/path/to/your/LLM Wiki`, and the `claude` binary path with your own.
   - **Reply** and **Say I am working** (WhatsApp nodes): set `YOUR_PHONE_NUMBER_ID` and attach your WhatsApp API credential.
3. Point your Meta webhook at the n8n webhook URL (path `whatsapp`), set a verify token, and let Meta's GET verification reach the **Auth -> Respond to Webhook** branch.
4. Subscribe the app to your WABA (gotcha 2).
5. Generate and use a permanent token (gotcha 3).

## Hard-won gotchas

1. **Do not use the official WhatsApp Trigger node.** It answers Meta's verification with a generic acknowledgement instead of echoing `hub.challenge`, so verification can never pass. This template uses two plain webhook nodes instead: a GET webhook wired to a Respond to Webhook node that echoes `hub.challenge`, and a POST webhook for the messages. Both share the path `whatsapp`.
2. **Subscribe the app to the WABA**, not just the messages field, or messages never arrive (`POST https://graph.facebook.com/v.../{WABA_ID}/subscribed_apps`).
3. **Use a permanent System-User token.** Meta test tokens expire after 24 hours.
4. **Unlock the keychain over SSH.** Claude Code's login token lives in the macOS login keychain, which is locked in a non-graphical SSH session, so the command unlocks it first. The host must stay powered on and logged in.
5. **Strip the boot noise.** Headless Claude prints its start-up block before the answer; the prompt asks Alex to wrap the answer in `<<<A>>> ... <<<Z>>>` markers, which the Prep Response node extracts with a regex.

## Security notes

- Keep your real Phone Number ID, WABA ID, access tokens, host paths, SSH credentials, and keychain password file out of version control.
- The SSH command unlocks your login keychain from a password file. Lock that file down (`chmod 600`) and never commit it.
