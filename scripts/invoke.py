#!/usr/bin/env python3
"""Send one prompt to a deployed agent and print its reply.

    python scripts/invoke.py "What can you do?"
    python scripts/invoke.py --speaker "Ana Souza" --session-id <id> "let's threat model the shop"

Documents in the reply, such as a written threat model, are saved to the current folder
and not printed.

The runtime ARN comes from --arn or the AGENT_RUNTIME_ARN environment variable
(the stack's AgentRuntimeArn output). The caller's AWS credentials need
bedrock-agentcore:InvokeAgentRuntime on it.
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

import boto3


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("prompt")
    parser.add_argument("--arn", default=os.environ.get("AGENT_RUNTIME_ARN"))
    parser.add_argument(
        "--session-id",
        default=f"cli-{uuid.uuid4()}",
        help="33 to 256 characters. Reuse a value to continue a conversation when memory is enabled.",
    )
    parser.add_argument("--actor-id", help="Who is asking; used to separate conversations in memory.")
    parser.add_argument("--speaker", help="The name of whoever is writing, as Slack would display it.")
    parser.add_argument(
        "--type", choices=["direct_message", "channel_thread"], default="direct_message",
        help="The kind of conversation. In a channel thread the agent may stay quiet.",
    )
    parser.add_argument("--unaddressed", action="store_true",
                        help="The message does not mention STRIDEr.")
    args = parser.parse_args(argv)

    if not args.arn:
        parser.error("set AGENT_RUNTIME_ARN or pass --arn")

    body = {"prompt": args.prompt, "conversationType": args.type, "addressed": not args.unaddressed}
    if args.actor_id:
        body["actorId"] = args.actor_id
    if args.speaker:
        body["speakerName"] = args.speaker

    # The region is the fourth field of the runtime ARN.
    client = boto3.client("bedrock-agentcore", region_name=args.arn.split(":")[3])
    response = client.invoke_agent_runtime(
        agentRuntimeArn=args.arn,
        runtimeSessionId=args.session_id,
        contentType="application/json",
        accept="application/json",
        payload=json.dumps(body).encode(),
    )
    reply = json.loads(response["response"].read())
    for document in reply.pop("documents", None) or []:
        name = Path(str(document.get("filename") or "document.md")).name
        Path(name).write_text(document.get("markdown", ""), encoding="utf-8")
        print(f"Saved {name}", file=sys.stderr)
    print(json.dumps(reply, indent=2))
    return 0 if reply.get("kind") in ("answer", "no_reply") else 1


if __name__ == "__main__":
    sys.exit(main())
