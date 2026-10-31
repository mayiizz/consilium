import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as taskApi from "../services/tasks";

export function useTasks(workspaceId: string, options?: { refetchInterval?: number | false }) {
  return useQuery({
    queryKey: ["tasks", workspaceId],
    queryFn: () => taskApi.listTasks(workspaceId),
    enabled: !!workspaceId,
    refetchInterval: options?.refetchInterval,
  });
}

export function useMoveTask(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: import("../../types").TaskStatus }) =>
      taskApi.moveTask(taskId, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks", workspaceId] }),
  });
}

export function useExtractTasks(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => taskApi.extractTasks(workspaceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks", workspaceId] });
      qc.invalidateQueries({ queryKey: ["kanban-review", workspaceId] });
    },
  });
}

export function useRebuildTasks(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => taskApi.rebuildTasks(workspaceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks", workspaceId] });
      qc.invalidateQueries({ queryKey: ["kanban-review", workspaceId] });
    },
  });
}

export function useUpdateTask(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, data }: { taskId: string; data: taskApi.UpdateTaskPayload }) =>
      taskApi.updateTask(taskId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks", workspaceId] }),
  });
}
