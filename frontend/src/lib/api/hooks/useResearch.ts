import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as researchApi from "../services/research";

export function useResearchJobs(workspaceId: string) {
  return useQuery({
    queryKey: ["research", workspaceId],
    queryFn: () => researchApi.listResearchJobs(workspaceId),
    enabled: !!workspaceId,
    refetchInterval: (q) => {
      const items = q.state.data ?? [];
      const busy = items.some(
        (j) =>
          j.status === "pending" ||
          j.status === "running" ||
          (j.phase && j.phase !== "completed" && j.status !== "failed" && j.status !== "done"),
      );
      return busy ? 4000 : false;
    },
  });
}

export function useCreateResearchJob(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      topic,
      constraints,
      researchType,
    }: {
      topic: string;
      constraints?: string;
      researchType?: string;
    }) =>
      researchApi.createResearchJob(
        workspaceId,
        topic,
        constraints ?? "",
        researchType ?? "general",
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["research", workspaceId] }),
  });
}

export function useRetryResearchJob(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => researchApi.retryResearchJob(workspaceId, jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["research", workspaceId] }),
  });
}
