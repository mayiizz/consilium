import { useQuery } from "@tanstack/react-query";
import * as analyticsApi from "../services/analytics";

export function useDashboard(workspaceId: string) {
  return useQuery({
    queryKey: ["dashboard", workspaceId],
    queryFn: () => analyticsApi.fetchDashboard(workspaceId),
    enabled: !!workspaceId,
  });
}

export function useAnalytics(workspaceId: string) {
  return useQuery({
    queryKey: ["analytics", workspaceId],
    queryFn: () => analyticsApi.fetchAnalytics(workspaceId),
    enabled: !!workspaceId,
  });
}

export function useRoadmap(workspaceId: string) {
  return useQuery({
    queryKey: ["roadmap", workspaceId],
    queryFn: () => analyticsApi.fetchRoadmap(workspaceId),
    enabled: !!workspaceId,
  });
}

export function useRisks(workspaceId: string) {
  return useQuery({
    queryKey: ["risks", workspaceId],
    queryFn: () => analyticsApi.fetchRisks(workspaceId),
    enabled: !!workspaceId,
  });
}

export function useTeam(workspaceId: string) {
  return useQuery({
    queryKey: ["team", workspaceId],
    queryFn: () => analyticsApi.fetchTeam(workspaceId),
    enabled: !!workspaceId,
  });
}

export function useDocuments(workspaceId: string) {
  return useQuery({
    queryKey: ["documents", workspaceId],
    queryFn: () => analyticsApi.listDocuments(workspaceId),
    enabled: !!workspaceId,
  });
}
