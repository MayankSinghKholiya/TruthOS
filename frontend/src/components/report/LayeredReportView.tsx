import { BookOpen, Fingerprint, Layers, ScrollText, Swords } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AmbiguityWarning } from "@/components/report/AmbiguityWarning";
import { ChallengeBox } from "@/components/report/ChallengeBox";
import { ConfidenceDashboard } from "@/components/report/ConfidenceDashboard";
import { CounterArguments } from "@/components/report/CounterArguments";
import { EvidenceList } from "@/components/report/EvidenceList";
import { References } from "@/components/report/References";
import { VerdictCard } from "@/components/report/VerdictCard";
import type { LayeredReport } from "@/types";

interface LayeredReportViewProps {
  report: LayeredReport;
  onChallenge?: (challengeText: string) => void;
  isBusy?: boolean;
}

export function LayeredReportView({ report, onChallenge, isBusy }: LayeredReportViewProps) {
  return (
    <div className="flex flex-col gap-4">
      {report.entity_ambiguity?.is_ambiguous && (
        <AmbiguityWarning ambiguity={report.entity_ambiguity} />
      )}
      <VerdictCard verdict={report.verdict} />

      <Tabs defaultValue="summary">
        <TabsList>
          <TabsTrigger value="summary">
            <ScrollText className="h-3.5 w-3.5" /> Summary
          </TabsTrigger>
          <TabsTrigger value="confidence">
            <Fingerprint className="h-3.5 w-3.5" /> Confidence
          </TabsTrigger>
          <TabsTrigger value="evidence">Evidence ({report.evidence.length})</TabsTrigger>
          <TabsTrigger value="counter">
            <Swords className="h-3.5 w-3.5" /> Counter ({report.counter_arguments.length})
          </TabsTrigger>
          <TabsTrigger value="deep-dive">
            <Layers className="h-3.5 w-3.5" /> Deep Dive
          </TabsTrigger>
          <TabsTrigger value="references">
            <BookOpen className="h-3.5 w-3.5" /> Refs ({report.references.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="summary">
          <Card className="relative overflow-hidden">
            <div className="absolute inset-y-0 left-0 w-[3px] bg-gradient-to-b from-primary to-gold" />
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ScrollText className="h-4 w-4 text-primary" /> Executive Summary
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="max-w-[65ch] text-[15px] leading-[1.75] text-foreground/90">
                {report.executive_summary}
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="confidence">
          <ConfidenceDashboard confidence={report.confidence} />
        </TabsContent>

        <TabsContent value="evidence">
          <EvidenceList evidence={report.evidence} />
        </TabsContent>

        <TabsContent value="counter">
          <CounterArguments counterArguments={report.counter_arguments} />
        </TabsContent>

        <TabsContent value="deep-dive">
          <Card className="relative overflow-hidden">
            <div className="absolute inset-y-0 left-0 w-[3px] bg-gradient-to-b from-primary to-gold" />
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-primary" /> Deep Dive
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="max-w-[65ch] whitespace-pre-wrap text-[15px] leading-[1.75] text-foreground/90">
                {report.deep_dive}
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="references">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-primary" /> References
              </CardTitle>
            </CardHeader>
            <CardContent>
              <References references={report.references} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {onChallenge && <ChallengeBox onSubmit={onChallenge} disabled={isBusy} />}
    </div>
  );
}
