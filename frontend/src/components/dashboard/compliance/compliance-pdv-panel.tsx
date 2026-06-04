"use client";

import type { CompliancePdvRule } from "./compliance-catalog";
import { ComplianceRulesPanel } from "./compliance-rules-panel";

type Props = {
  rules: CompliancePdvRule[];
  forceVisible?: boolean;
};

export function CompliancePdvPanel({ rules, forceVisible }: Props) {
  return (
    <ComplianceRulesPanel
      rules={rules}
      forceVisible={forceVisible}
      variant="blue"
      title="Kad uđeš u PDV — pravila na jednom mjestu"
      subtitle="Informativni pregled obveza u PDV sustavu. Za odluke koristite računovođu."
    />
  );
}
