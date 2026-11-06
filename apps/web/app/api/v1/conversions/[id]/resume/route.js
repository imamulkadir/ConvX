import {
  runtime as service,
  respond,
  originCheck,
} from "../../../../../../lib/server/runtime.mjs";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function POST(request, context) {
  return respond(async () => {
    originCheck(request);
    return service().resume((await context.params).id);
  });
}
