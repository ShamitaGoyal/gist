export type TopicGroup = {
  id: string;
  name: string;
  documentIds: string[];
  createdAt: string;
};

const STORAGE_KEY = "gist-groups";

export function readGroups(): TopicGroup[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.flatMap((item) => {
      if (!item || typeof item !== "object") return [];
      const group = item as Partial<TopicGroup>;
      if (typeof group.id !== "string" || typeof group.name !== "string") return [];
      const documentIds = Array.isArray(group.documentIds)
        ? group.documentIds.filter((id): id is string => typeof id === "string")
        : [];
      return [{
        id: group.id,
        name: group.name,
        documentIds,
        createdAt: typeof group.createdAt === "string" ? group.createdAt : new Date().toISOString(),
      }];
    });
  } catch {
    return [];
  }
}

export function writeGroups(groups: TopicGroup[]) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(groups));
}
