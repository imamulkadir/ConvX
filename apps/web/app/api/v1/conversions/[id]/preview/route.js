import {
  runtime as service,
  respond,
} from "../../../../../../lib/server/runtime.mjs";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(request, context) {
  return respond(async () => {
    const url = new URL(request.url);
    return service().preview(
      (await context.params).id,
      url.searchParams.get("kind"),
      Number(url.searchParams.get("page") || 1),
    );
  });
}
