import {
  runtime as service,
  respond,
  originCheck,
} from "../../../../../lib/server/runtime.mjs";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(_request, context) {
  return respond(async () => service().status((await context.params).id));
}
export async function DELETE(request, context) {
  return respond(async () => {
    originCheck(request);
    return service().remove((await context.params).id);
  });
}
