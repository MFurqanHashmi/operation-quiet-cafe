import type { Actor } from "./types";

export interface MissionMeta {
  n: number;
  room: string;
  roomName: string;
  actor: Actor;
  youAre: "now" | "still";
  title: string;
  concept: string;
  seat: string;            // e.g. "Eavesdropper"
  brief: string;           // in-world scene set-up
  running: string;         // what auto-plays around you
  goal: string;            // the objective line
  hints: string[];         // progressive nudges
  debrief: string;         // payoff after the code
  whyItMatters: string;    // single woven paragraph (no tracks)
  codeHint: string;        // where the code surfaces
}

export const ACTOR_LABEL: Record<Actor, string> = {
  alice: "Alice",
  bob: "Bob",
  eve: "Eve",
};

export const MISSIONS: MissionMeta[] = [
  {
    n: 1,
    room: "open_floor",
    roomName: "The Open Floor",
    actor: "eve",
    youAre: "now",
    title: "The Open Road",
    concept: "How data moves",
    seat: "Eavesdropper",
    brief:
      "You slip into the chair two tables over. Alice and Bob think the café Wi-Fi is private. You open your laptop and start listening.",
    running:
      "Alice and Bob are chatting on a loop right now — every line is crossing the open air between them.",
    goal: "Tap the wire and read what they're saying. Somewhere in that chatter is today's code word.",
    hints: [
      "Nothing here is locked. You don't need to break anything — just read.",
      "Watch the messages scroll. One line is literally handing you a code word.",
      "The code word is wrapped in QC{...}. Copy it exactly, braces and all.",
    ],
    debrief:
      "That's the whole problem in one move. On an open network, every word is a postcard — anyone two tables over can read it. This is why the rest of the café exists.",
    whyItMatters:
      "For the people approving the budget, this is the cost of 'we'll add security later' — until you encrypt, every message is a postcard. For the people writing the code, it's why http:// and plaintext anything (logs, tokens, internal calls) is a quiet liability even inside a 'trusted' network.",
    codeHint: "It scrolls past in the tapped conversation — read Alice's third line.",
  },
  {
    n: 2,
    room: "cipher_bench",
    roomName: "The Cipher Bench",
    actor: "alice",
    youAre: "now",
    title: "Scramble It",
    concept: "Encryption & symmetric keys",
    seat: "Sender",
    brief:
      "You leave Eve's corner and take your own seat. You're Alice now, and you've learned your lesson — this message goes out scrambled.",
    running: "Bob is waiting at the bench, ready to unscramble whatever you send.",
    goal:
      "Write a message, scramble it, and send it to Bob. He'll reply with the code word. Then ask the obvious question: how did Bob get the key?",
    hints: [
      "Type anything, hit Scramble, and watch readable text turn to noise.",
      "Send the scrambled message — Bob shares the same key, so he can read it. His reply carries the code.",
      "Then press 'Send Bob the key' and watch the wire. Notice who else just caught it.",
    ],
    debrief:
      "One key locked it AND unlocked it — that's symmetric encryption: fast and simple. But you just watched the catch: to use it, Alice and Bob both need the same key, and the moment you send it, Eve grabs it too. That's the wall Mission 3 breaks.",
    whyItMatters:
      "For the strategy side, this is why 'just encrypt it' is never the whole story — the hard, expensive part is key distribution, not the scrambling. For the build side, it's the intuition behind why we don't ship a shared secret in the repo or pass one over the same channel we're trying to protect.",
    codeHint: "Bob's reply contains it — but only after he successfully unscrambles your message.",
  },
  {
    n: 3,
    room: "key_exchange",
    roomName: "The Key Exchange",
    actor: "alice",
    youAre: "still",
    title: "Two Keys",
    concept: "Asymmetric / public-key",
    seat: "Sender",
    brief:
      "Still Alice. Bob has pinned a public padlock to the board — anyone can take it, but only Bob can open what it locks.",
    running: "Eve is still recording everything that crosses the wire. Let her.",
    goal:
      "Grab Bob's public key, lock your message with it, and send. Bob opens it with his private key. Check what Eve captured.",
    hints: [
      "First fetch Bob's public padlock. Note its fingerprint — you'll meet that idea again next mission.",
      "Lock your message with Bob's PUBLIC key, then send. His PRIVATE key is the only thing that opens it.",
      "Open Eve's recording — this time it's pure noise. Bob's reply has the code.",
    ],
    debrief:
      "Two different keys: one you hand to the whole world, one you never share. Alice never had to send Bob a secret — and Eve recorded the entire exchange and got nothing but noise. That's the leap that makes the internet possible. (Curious how they agree on a key without sending one at all? Open the Tradecraft below.)",
    whyItMatters:
      "For the decision-makers, this is the quiet machinery behind every 'https' and every secure login your product relies on — worth knowing it exists and why it's non-negotiable. For the engineers, it's the difference between symmetric and asymmetric crypto, and why TLS uses the slow two-key dance only to bootstrap a fast shared key.",
    codeHint: "Inside Bob's decrypted reply — which only works via the public/private key path.",
  },
  {
    n: 4,
    room: "hall_of_padlocks",
    roomName: "The Hall of Padlocks",
    actor: "alice",
    youAre: "still",
    title: "The Padlock Lies",
    concept: "Certificates & trust",
    seat: "Inspector",
    brief:
      "New job, same seat: today you verify. Two doors both claim to be Bob's drop site. Both show a padlock. Only one is really him.",
    running: "An impostor has set up a look-alike door, hoping you won't check the details.",
    goal:
      "Inspect both doors' certificates. Compare each fingerprint against Bob's known-good one, then walk through the real door.",
    hints: [
      "Inspect each door. A padlock alone means 'encrypted' — not 'trustworthy'.",
      "Compare each door's fingerprint and issuer to Bob's known-good fingerprint shown at the top.",
      "The impostor's cert is self-signed by an unknown issuer and the fingerprint won't match. Choose the door that does.",
    ],
    debrief:
      "Both lines were encrypted. One was encrypted straight to an impostor. The padlock only ever proved the connection was locked — never who was holding the other end. That's what certificates and trusted issuers are for.",
    whyItMatters:
      "For the business, this is why 'it has the padlock, it's safe' is a dangerous half-truth your teams and customers fall for in phishing. For engineers, it's why we pin/verify certificates and don't blindly set verify=False to make an error go away.",
    codeHint: "The genuine door serves it on entry; the impostor only throws a warning.",
  },
  {
    n: 5,
    room: "station_bravo",
    roomName: "Station Bravo",
    actor: "bob",
    youAre: "now",
    title: "No Password on the Wire",
    concept: "SSH & key-based login",
    seat: "Operator",
    brief:
      "You flip sides for good. You're Bob now — defending the very station everyone's been trying to reach. Attackers are hammering the door with password guesses.",
    running: "Eve is in the corner trying password after password against your station. Each one bounces.",
    goal:
      "Log in the right way: generate a key, install its public half on the station, and connect with key auth — no password ever crosses the wire.",
    hints: [
      "Press 'Secure login'. Watch each step: a fresh key is made, the public half is installed, then you connect.",
      "Notice the order — only the PUBLIC half is ever sent to the station. Your private key never leaves your laptop.",
      "After login, your sealed orders (the code) are read straight off the station.",
    ],
    debrief:
      "Eve can guess passwords forever and never get in, because there's no password to guess. Your private key stayed on your laptop the whole time; only the public half — useless on its own — ever touched the station. That's why SSH key auth beats passwords.",
    whyItMatters:
      "For leadership, this reframes credentials: the strongest login is the one where the secret never travels and can't be phished or guessed. For engineers, it's the everyday case for SSH keys (and disabling password auth) on every server and Git host you touch.",
    codeHint: "It's a file waiting on the station — readable only after a real key-based login.",
  },
  {
    n: 6,
    room: "the_vault",
    roomName: "The Vault",
    actor: "bob",
    youAre: "still",
    title: "Kill the Password",
    concept: "TOTP & passkeys",
    seat: "Gatekeeper",
    brief:
      "Still Bob, at the vault door of your drop site. The old password field is crossed out. Two modern locks remain: a rotating code, and a passwordless key.",
    running: "Eve has given up guessing — there's nothing left for her to steal.",
    goal:
      "First prove a rotating code (TOTP) works. Then retire the password entirely with a passwordless challenge to open the vault.",
    hints: [
      "Reveal the authenticator. The 6-digit code is derived from a shared seed + the clock — submit the live one.",
      "Then request a passkey challenge. Your device signs a one-time challenge instead of sending any secret.",
      "When the signature verifies, the vault opens and hands you the final code.",
    ],
    debrief:
      "A rotating code means an intercepted login is useless within 30 seconds. A passkey goes further — there's no shared secret at all, just a signature only your device can produce. You can't steal a password that doesn't exist.",
    whyItMatters:
      "For the org, this is the punchline of the whole talk: stolen credentials cause most breaches, and passkeys delete the thing being stolen — fewer takeovers, less phishing risk. For engineers, it's why TOTP/WebAuthn and passwordless flows are worth the integration cost.",
    codeHint: "The vault releases it only after a passwordless challenge verifies.",
  },
];

export const ACTORS: Actor[] = ["alice", "bob", "eve"];
