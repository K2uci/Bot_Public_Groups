"use client";

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <main className="narrow">
      <h1>Algo salió mal</h1>
      <p className="error">{error.message}</p>
      <button onClick={() => reset()}>Reintentar</button>
    </main>
  );
}
