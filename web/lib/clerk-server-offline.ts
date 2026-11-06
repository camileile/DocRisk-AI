import { NextResponse } from "next/server";
export function clerkMiddleware() { return () => NextResponse.next(); }
