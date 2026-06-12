import React from "react";
import { useStore } from "../store";
import { Button } from "./ui";

export function ColdOpen() {
  const { goPhase } = useStore();
  return (
    <div className="coldopen">
      <div className="co-card">
        <div className="co-kicker">Operation</div>
        <h1 className="co-title">Quiet Café</h1>
        <p className="co-lede">
          A message has to reach an agent across a crowded café &mdash; past <span className="t-eve">Eve</span>,
          who's listening from two tables over. Over six moves you'll slip into every chair at the table:
          first <span className="t-eve">Eve</span> the eavesdropper, then <span className="t-alice">Alice</span> the
          sender, then <span className="t-bob">Bob</span> the one who has to lock it all down.
        </p>
        <ul className="co-rules">
          <li>You wear <strong>one hat at a time</strong>. Whoever you're not playing runs automatically around you.</li>
          <li>Watch the three screens &mdash; that's the whole café playing out live.</li>
          <li>Each mission hides a <strong>confirmation code</strong>. You can't guess it; you have to earn it.</li>
        </ul>
        <Button onClick={() => goPhase("playing")}>Take your seat &rarr;</Button>
      </div>
    </div>
  );
}

export function CaseClosed() {
  const { reset } = useStore();
  return (
    <div className="coldopen">
      <div className="co-card">
        <div className="co-kicker">Case Closed</div>
        <h1 className="co-title">Eve got nothing.</h1>
        <p className="co-lede">
          You sat in every chair. As <span className="t-eve">Eve</span> you read a postcard off the open air.
          As <span className="t-alice">Alice</span> you scrambled it, then handed out a padlock without ever
          sharing a secret. As <span className="t-bob">Bob</span> you shut the door on passwords entirely.
          The eavesdropper was at the table the whole time &mdash; and never got a thing.
        </p>
        <p className="co-lede co-bookend">
          That's the question we opened with: why can't the person two tables over read it? Now it's in your hands.
        </p>
        <Button onClick={reset}>Run it again</Button>
      </div>
    </div>
  );
}
