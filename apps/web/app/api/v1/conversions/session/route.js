import {
  runtime as service,
  respond,
} from "../../../../../lib/server/runtime.mjs";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET() {
  return respond(async () => {
    await service().init();
    return service().limits;
  });
}
