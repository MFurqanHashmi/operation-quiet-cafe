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
  checkpoint?: {           // deduction MCQ (answer validated server-side by index)
    prompt: string;
    options: string[];
  };
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
      "Alice, Bob, the barista, an ad beacon and the router are all chattering on the open air — a realistic jumble of traffic, only some of it sensitive.",
    goal: "Tap the wire. Six messages crossed it in the clear — but only one would actually compromise the operation. Read them, judge them, and flag the real leak.",
    hints: [
      "Nothing here is locked, so read everything. The skill isn't decoding — it's judgement: which line actually helps an attacker?",
      "Ignore the noise that only LOOKS sensitive — a promo code, an internal IP, even the café's public guest Wi-Fi password. Those cost an attacker nothing.",
      "Find the line that exposes the operation itself — a place, a time, a combination. Flag that one to pull today's code.",
    ],
    debrief:
      "That's the whole problem in one move. On an open network, every word is a postcard — anyone two tables over can read it. This is why the rest of the café exists.",
    whyItMatters:
      "For the people approving the budget, this is the cost of 'we'll add security later' — until you encrypt, every message is a postcard. For the people writing the code, it's why http:// and plaintext anything (logs, tokens, internal calls) is a quiet liability even inside a 'trusted' network.",
    codeHint: "Flag the one message that truly leaks the operation. Pick right and the code is yours; pick a decoy and you'll get a nudge.",
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
    running: "Bob is waiting at the bench, ready to unscramble whatever you send — if only he had the key. Eve is still listening.",
    goal:
      "Scramble a message, then make the real call: how do you get the shared key to Bob? Try it, watch what happens, then answer why it failed.",
    hints: [
      "Type anything and hit Scramble — readable text turns to noise. That part's easy. The hard part is the key.",
      "You must pick how to deliver the key to Bob. Go ahead and try the obvious one and watch the wire — the failure is the lesson.",
      "Once you've seen it go wrong, the checkpoint asks WHY. The answer isn't about the cipher — it's about the key being the same on both ends and travelling in the open.",
    ],
    debrief:
      "One key locked it AND unlocked it — that's symmetric encryption: fast and simple. But you just watched the catch: to use it, Alice and Bob both need the same key, and the moment you send it, Eve grabs it too. That's the wall Mission 3 breaks.",
    whyItMatters:
      "For the strategy side, this is why 'just encrypt it' is never the whole story — the hard, expensive part is key distribution, not the scrambling. For the build side, it's the intuition behind why we don't ship a shared secret in the repo or pass one over the same channel we're trying to protect.",
    codeHint: "It's released when you correctly diagnose why Eve could read the message — answer the checkpoint to earn it.",
    checkpoint: {
      prompt: "Eve read your message the instant the key crossed the wire. Why?",
      options: [
        "The AES encryption was too weak to hold up",
        "The same key both locks and unlocks — and it travelled in the open",
        "Bob accidentally used the wrong key to decrypt",
      ],
    },
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
    running: "Eve is still recording everything — and her own public key is sitting on the board too, hoping you'll grab the wrong one.",
    goal:
      "Your keyring shows three public keys — Bob's, Eve's, and your own. Lock the message so ONLY Bob can open it. Choose carefully: the wrong padlock plays out for real.",
    hints: [
      "A public key locks; only the matching private key unlocks. So whose key should you lock with — the sender's, or the person you want to read it?",
      "Lock with Eve's key and Eve's private key opens it. Lock with your OWN key and only you could open it — Bob can't. Neither reaches Bob safely.",
      "To reach Bob and only Bob, lock with Bob's public key. His private key is the one thing on earth that opens it.",
    ],
    debrief:
      "Two different keys: one you hand to the whole world, one you never share. Alice never had to send Bob a secret — and Eve recorded the entire exchange and got nothing but noise. That's the leap that makes the internet possible. (Curious how they agree on a key without sending one at all? Open the Tradecraft below.)",
    whyItMatters:
      "For the decision-makers, this is the quiet machinery behind every 'https' and every secure login your product relies on — worth knowing it exists and why it's non-negotiable. For the engineers, it's the difference between symmetric and asymmetric crypto, and why TLS uses the slow two-key dance only to bootstrap a fast shared key.",
    codeHint: "Inside Bob's decrypted reply — which only appears when you've locked with the correct key (his).",
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
      "Inspect both doors' certificates and compare each fingerprint to Bob's known-good one. Walk through the real door — pick wrong and you'll find out who's really behind it. Then say what gave the fake away.",
    hints: [
      "Inspect both doors. Don't be fooled by the name or the padlock — anyone can copy a name, and both lines are encrypted.",
      "The one thing that can't be faked is the fingerprint. Compare each door's against Bob's known-good value at the top.",
      "Pick the door whose fingerprint matches exactly. Then the checkpoint asks what exposed the fake — focus on the fingerprint, not the name or the padlock.",
    ],
    debrief:
      "Both lines were encrypted. One was encrypted straight to an impostor. The padlock only ever proved the connection was locked — never who was holding the other end. That's what certificates and trusted issuers are for.",
    whyItMatters:
      "For the business, this is why 'it has the padlock, it's safe' is a dangerous half-truth your teams and customers fall for in phishing. For engineers, it's why we pin/verify certificates and don't blindly set verify=False to make an error go away.",
    codeHint: "Verify the real door, then nail the checkpoint on what exposed the fake — the code is released once you've done both.",
    checkpoint: {
      prompt: "Both doors showed a padlock and an encrypted line. What actually exposed the impostor?",
      options: [
        "The impostor had no padlock / no encryption",
        "The impostor's name was different from Bob's",
        "The impostor's fingerprint didn't match Bob's known-good one",
      ],
    },
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
    running: "Eve is in the corner trying password after password against your station. Each one bounces — and she'll keep at it while you set up the right way in.",
    goal:
      "Generate your key pair, then make the call: which key do you install on the station? Choose wrong and you'll see the damage. Get in, then explain what actually crossed the wire.",
    hints: [
      "You made two keys. One is safe to publish anywhere; one must never leave this laptop. Which one does a server need to recognise you?",
      "Installing your PRIVATE key on a shared box is the tempting mistake — now anyone who breaches it becomes you. The server only ever needs your PUBLIC key.",
      "Install the public key, log in by signature, then answer the checkpoint: nothing reusable — not your password, not your private key — ever crosses the wire.",
    ],
    debrief:
      "Eve can guess passwords forever and never get in, because there's no password to guess. Your private key stayed on your laptop the whole time; only the public half — useless on its own — ever touched the station. That's why SSH key auth beats passwords.",
    whyItMatters:
      "For leadership, this reframes credentials: the strongest login is the one where the secret never travels and can't be phished or guessed. For engineers, it's the everyday case for SSH keys (and disabling password auth) on every server and Git host you touch.",
    codeHint: "Read off the station after a real key-based login — released once you also answer what crossed the wire.",
    checkpoint: {
      prompt: "You logged in with a key, no password typed. During that login, what actually crossed the wire?",
      options: [
        "Your password, but encrypted",
        "Your private key, sent securely to the server",
        "Only a signature proving you hold the private key — the key itself never moved",
      ],
    },
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
      "Test the rotating code two ways — try replaying an old one, then the live one — to feel why it's time-bound. Then go passwordless to open the vault, and explain why a passkey can't be phished.",
    hints: [
      "Reveal the authenticator, then deliberately try the 'replay an old code' button. Watch the vault reject it — a recorded code is useless seconds later.",
      "Now submit the LIVE code; it's accepted. Then request a passkey challenge — your device signs it instead of sending any secret.",
      "After the signature verifies, the checkpoint asks why passkeys resist phishing. The key idea: the server stores no secret to steal, and there's nothing to type into a fake site.",
    ],
    debrief:
      "A rotating code means an intercepted login is useless within 30 seconds. A passkey goes further — there's no shared secret at all, just a signature only your device can produce. You can't steal a password that doesn't exist.",
    whyItMatters:
      "For the org, this is the punchline of the whole talk: stolen credentials cause most breaches, and passkeys delete the thing being stolen — fewer takeovers, less phishing risk. For engineers, it's why TOTP/WebAuthn and passwordless flows are worth the integration cost.",
    codeHint: "Released after your passwordless login verifies and you answer why passkeys beat phishing.",
    checkpoint: {
      prompt: "Phishing thrives on stealing a secret you type. Why are passkeys phishing-resistant?",
      options: [
        "The password is just much longer and harder to guess",
        "There's no shared secret stored on the server for anyone to steal or phish",
        "The 6-digit code rotates every 30 seconds",
      ],
    },
  },
];

export const ACTORS: Actor[] = ["alice", "bob", "eve"];
