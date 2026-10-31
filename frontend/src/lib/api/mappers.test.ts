import { describe, it, expect } from "vitest";
import { mapTaskStatus, mapTaskStatusToApi, mapRole, mapTask } from "./mappers";

describe("api mappers", () => {
  it("maps task statuses bidirectionally", () => {
    expect(mapTaskStatus("In Progress")).toBe("in_progress");
    expect(mapTaskStatusToApi("in_progress")).toBe("In Progress");
  });

  it("maps lead to manager", () => {
    expect(mapRole("lead")).toBe("manager");
    expect(mapRole("member")).toBe("member");
  });

  it("maps task response", () => {
    const task = mapTask({
      id: "1",
      title: "Test",
      status: "To Do",
      priority: "high",
      task_key: "MM-ABCD1234",
      is_auto_generated: true,
      description_user_set: false,
      description: "hidden auto text",
      source_meeting_id: "m1",
    });
    expect(task.status).toBe("todo");
    expect(task.taskKey).toBe("MM-ABCD1234");
    expect(task.aiGenerated).toBe(true);
    expect(task.description).toBeUndefined();
    expect(task.sourceMeetingId).toBe("m1");
  });
});
