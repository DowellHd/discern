/**
 * Back Soon switch. While true, the root layout renders the Back Soon page in
 * place of every route, so the app (and its API calls) never mounts.
 * Set NEXT_PUBLIC_BACK_SOON=false at build time to restore the full app.
 */
export const BACK_SOON = process.env.NEXT_PUBLIC_BACK_SOON !== "false";
