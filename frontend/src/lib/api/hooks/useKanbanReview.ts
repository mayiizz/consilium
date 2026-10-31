import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as kanbanReviewApi from "../services/kanbanReview";

export function useKanbanReviewQueue(workspaceId: string, enabled = true) {
  return useQuery({
    queryKey: ["kanban-review", workspaceId],
    queryFn: () => kanbanReviewApi.listKanbanReviewQueue(workspaceId),
    enabled: !!workspaceId && enabled,
  });
}

export function useApproveKanbanReview(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reviewId: string) => kanbanReviewApi.approveKanbanReview(workspaceId, reviewId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["kanban-review", workspaceId] });
      qc.invalidateQueries({ queryKey: ["tasks", workspaceId] });
    },
  });
}

export function useRejectKanbanReview(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reviewId: string) => kanbanReviewApi.rejectKanbanReview(workspaceId, reviewId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kanban-review", workspaceId] }),
  });
}
