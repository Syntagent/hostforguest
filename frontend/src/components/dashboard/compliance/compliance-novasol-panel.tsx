"use client";

import type { CompliancePdvRule } from "./compliance-catalog";
import { ComplianceRulesPanel } from "./compliance-rules-panel";

type Props = {
  rules: CompliancePdvRule[];
  forceVisible?: boolean;
};

export function ComplianceNovasolPanel({ rules, forceVisible }: Props) {
  return (
    <ComplianceRulesPanel
      rules={rules}
      forceVisible={forceVisible}
      variant="emerald"
      title="Iznajmljivanje preko Novasola — što vrijedi"
      subtitle="Informativni pregled suradnje s agencijom. Detalji ovise o vašem ugovoru i poreznom statusu."
    />
  );
}
