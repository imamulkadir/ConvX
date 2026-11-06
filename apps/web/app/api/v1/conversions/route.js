import {
  runtime as service,
  respond,
} from "../../../../lib/server/runtime.mjs";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function POST(request) {
  return respond(async () =>
    Response.json(await service().create(request), {
      status: 202,
      headers: { "Cache-Control": "no-store" },
    }),
  );
}
