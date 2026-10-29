"use client";

import { setNonce } from "get-nonce";
import { useInsertionEffect, type ReactNode } from "react";

export function CspStyleNonce({ nonce, children }: { nonce: string; children: ReactNode }) {
  // react-style-singleton (Radix scroll locking) reads this nonce when it
  // creates its style element. Configure before passive library effects;
  // never mutate shared module state during server rendering.
  useInsertionEffect(() => {
    setNonce(nonce);
  }, [nonce]);
  return children;
}
