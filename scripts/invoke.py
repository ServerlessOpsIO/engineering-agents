#!/usr/bin/env python3
"""Send one prompt to a deployed agent and print its reply.

    python scripts/invoke.py "What can you do?"

The runtime ARN comes from --arn or the AGENT_RUNTIME_ARN environment variable
(the stack's AgentRuntimeArn output). The caller's AWS credentials need
bedrock-agentcore:InvokeAgentRuntime on it.
"""

import argparse
import json
import os
import sys
import uuid

import boto3


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("prompt")
    parser.add_argument("--arn", default=os.environ.get("AGENT_RUNTIME_ARN"))
    parser.add_argument(
        "--session-id",
        default=f"cli-{uuid.uuid4()}",
        help="33 to 256 characters. Reuse a value to continue a conversation when memory is enabled.",
    )
    parser.add_argument("--actor-id", help="Who is asking; used to separate conversations in memory.")
    args = parser.parse_args()

    if not args.arn:
        parser.error("set AGENT_RUNTIME_ARN or pass --arn")

    body = {"prompt": args.prompt}
    if args.actor_id:
        body["actorId"] = args.actor_id

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
    print(json.dumps(reply, indent=2))
    return 0 if reply.get("kind") == "answer" else 1


if __name__ == "__main__":
    sys.exit(main())
