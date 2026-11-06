import {
  runtime as service,
  respond,
} from "../../../../../../lib/server/runtime.mjs";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(_request, context) {
  return respond(async () => service().validation((await context.params).id));
}
