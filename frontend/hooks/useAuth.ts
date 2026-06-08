"use client";

import { useState, useEffect } from "react";
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  User,
} from "firebase/auth";
import { auth } from "@/lib/firebase";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!auth) {
      setLoading(false);
      return;
    }

    // Fallback: se onAuthStateChanged não responder em 2s (API key inválida),
    // marca como não autenticado para evitar tela branca infinita.
    const timer = setTimeout(() => setLoading(false), 2000);

    const unsubscribe = onAuthStateChanged(auth, (u) => {
      clearTimeout(timer);
      setUser(u);
      setLoading(false);
    });

    return () => {
      clearTimeout(timer);
      unsubscribe();
    };
  }, []);

  const login = (email: string, password: string) =>
    signInWithEmailAndPassword(auth!, email, password);

  const register = (email: string, password: string) =>
    createUserWithEmailAndPassword(auth!, email, password);

  const logout = () => signOut(auth!);

  return { user, loading, login, register, logout };
}
