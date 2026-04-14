export const frontendArchitecture = {
  activeAppRoot: "frontend/app",
  sourceOfTruth: [
    "frontend/app/layout.tsx",
    "frontend/app/lib/contracts.ts",
    "frontend/app/lib/api.ts",
    "frontend/app/lib/architecture.ts",
    "frontend/app/(legacy)",
  ],
  routePolicy: {
    activeRoutes: "Routes at frontend/app/* are current and supported.",
    legacyRoutes: "Legacy compatibility routes must live under a hidden route group at frontend/app/(legacy).",
  },
  legacyCompatibility: {
    supportedRouteAliases: ["/v14", "/v15", "/v16"],
    behavior: "Redirect to / while keeping legacy routing isolated from the active app surface.",
  },
} as const;
