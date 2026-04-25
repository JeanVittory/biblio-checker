import { Hero } from "@/components/landing/Hero";
import { ProblemSection } from "@/components/landing/ProblemSection";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { DemoScore } from "@/components/landing/DemoScore";
import { UseCases } from "@/components/landing/UseCases";
import { Sources } from "@/components/landing/Sources";
import { FinalCTA } from "@/components/landing/FinalCTA";

/**
 * Landing page — the public marketing surface at `/`.
 * Spec: landing-page/03-marketing-layout §6
 *
 * MUST remain a server component. Only DemoScore is a client island.
 * Wrapped by app/(marketing)/layout.tsx which provides MarketingHeader and
 * MarketingFooter.
 */
export default function LandingPage() {
  return (
    <>
      <Hero />
      <ProblemSection />
      <HowItWorks />
      <DemoScore />
      <UseCases />
      <Sources />
      <FinalCTA />
    </>
  );
}
