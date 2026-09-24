/**
 * Become-a-seller route (Phase 4.1) — protected: applicants need an account.
 */
import { Navbar } from "../components/layout/Navbar";
import { BecomeSellerForm } from "../features/seller/BecomeSellerForm";

export function BecomeSeller() {
  return (
    <div className="min-h-screen bg-sand-50 dark:bg-night-950">
      <Navbar />
      <main className="mx-auto max-w-lg px-4 py-12">
        <BecomeSellerForm />
      </main>
    </div>
  );
}