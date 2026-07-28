import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { t } from "@/i18n";
import { usePin } from "@/store/pin";

import { PinSetupModal } from "./PinSetupModal";
import { clearPin } from "./pinStorage";

export function PinSection() {
  const enabled = usePin((s) => s.enabled);
  const refresh = usePin((s) => s.refresh);
  const [showSetup, setShowSetup] = useState(false);

  const disable = () => {
    if (!confirm(t("pin.disable.confirm"))) return;
    clearPin();
    refresh();
  };

  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-[15px] font-medium">{t("pin.section.title")}</h2>
      <p className="text-[13px] text-[color:var(--text-soft)]">
        {enabled ? t("pin.section.on") : t("pin.section.off")}
      </p>
      <div className="flex flex-col gap-2">
        {enabled ? (
          <>
            <Button variant="secondary" size="md" onClick={() => setShowSetup(true)}>
              {t("pin.section.change")}
            </Button>
            <Button variant="danger" size="md" onClick={disable}>
              {t("pin.section.disable")}
            </Button>
          </>
        ) : (
          <Button variant="primary" size="md" onClick={() => setShowSetup(true)}>
            {t("pin.section.enable")}
          </Button>
        )}
      </div>
      {showSetup && <PinSetupModal onClose={() => setShowSetup(false)} />}
    </div>
  );
}
