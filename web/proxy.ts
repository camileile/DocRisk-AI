import { clerkMiddleware } from "@docrisk/clerk-server";
import { NextResponse, type NextRequest, type NextFetchEvent } from "next/server";
const clerk = clerkMiddleware();
export default function proxy(request: NextRequest, event: NextFetchEvent) {
  if (process.env.NEXT_PUBLIC_AUTH_MODE !== "clerk") return NextResponse.next();
  // As telas da demo são públicas. A autorização de cada operação é feita na FastAPI.
  return clerk(request, event);
}
export const config = { matcher: ["/((?!_next|.*\\.(?:css|js|png|svg|ico|woff2?)).*)"] };
