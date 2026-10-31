# Day 1 — Project Kickoff Meeting Transcript

**Project:** AI-Based 3D Mapping & Visualization System
**Day:** 1 — Project Kickoff
**Duration:** Approximately 1 hour
**Participants:** Rahul, Meera, Arjun, Ananya, Karthik

---

**[10:00 AM — Meeting Started]**

**Rahul:** Good morning everyone. So today is basically our Day 1. The main goal is to understand what we're building, divide the work, and decide what we need to complete first.

**Meera:** Yeah. Do we already have the final requirements or are we still figuring those out?

**Rahul:** We have the basic requirements. But some parts are still open, so we’ll finalize those today.

**Arjun:** Okay. What's the main workflow we're thinking about?

**Rahul:** The basic idea is that the user provides the input data, our system processes it, generates the required output, and then displays the result through the web interface.

**Ananya:** What kind of input are we expecting exactly? Images, videos, or both?

**Rahul:** Initially, we're thinking about images and video as the main inputs. But we should first confirm which one gives us a more realistic scope for the first prototype.

**Karthik:** I think we should start with images. Video processing might make the first version unnecessarily complicated.

**Ananya:** I agree. We can design the architecture to support video later, but keep the first prototype focused on images.

**Meera:** That would also make the UI simpler. We can have an upload section where the user uploads the images and then starts the processing.

**Arjun:** And from the backend side, we can create an upload API first. Later, we can connect that API to the ML service.

**Rahul:** Good. So let's keep the first milestone small.

---

**[10:08 AM — Requirement Discussion]**

**Rahul:** Let's go through the requirements one by one. What should the user be able to do?

**Meera:** Upload the input files.

**Arjun:** Start the processing.

**Ananya:** Then the ML pipeline should generate the required output.

**Karthik:** And the processed result should be stored somewhere so the user can access it.

**Meera:** We should also show processing status. If the processing takes a few minutes, the user shouldn't just see a blank screen.

**Arjun:** That's easy enough. We can have statuses like "Uploaded", "Processing", "Completed", and "Failed".

**Rahul:** Good idea.

**Ananya:** We should also consider what happens if the input isn't good enough. For example, if the images are blurry or there aren't enough overlapping images.

**Rahul:** That's important. We shouldn't assume every input will work.

**Karthik:** We can add basic validation during preprocessing.

**Meera:** Can we show an error message explaining what went wrong?

**Arjun:** Yes. The backend can return an error code and message, and the frontend can display it.

**Rahul:** Good. Let's write that down as a requirement.

---

**[10:15 AM — Technical Approach]**

**Rahul:** Now let's talk about the technical approach. Ananya, what are you thinking for the AI side?

**Ananya:** I don't want to commit to a specific model yet. First I want to understand the available datasets and test a few approaches.

**Arjun:** Are we planning to train our own model?

**Ananya:** Not necessarily. If there is a suitable pretrained model, we should use it. Training from scratch could take too much time and computing power.

**Karthik:** That also depends on the dataset. I'll search for datasets that match our requirements and check their licenses.

**Rahul:** Good. We should make sure we can legally use the data in our project.

**Ananya:** I'll also check whether the datasets have enough variation. If all the images look similar, our model might perform well during testing but fail on real-world inputs.

**Karthik:** I'll check that as part of the data analysis.

**Meera:** What about the frontend technology?

**Arjun:** I'd suggest we use something we're already comfortable with rather than trying something completely new.

**Meera:** I'm comfortable with React, so I can use that.

**Rahul:** Fine. And backend?

**Arjun:** We can use Python with FastAPI. That will make it easier to communicate with the ML service.

**Ananya:** FastAPI works for me.

**Rahul:** Okay. Let's go with that for the prototype.

---

**[10:24 AM — System Architecture Discussion]**

**Arjun:** I have one question about the architecture. Do we want the ML model inside the backend application or as a separate service?

**Ananya:** Separate service would be better.

**Arjun:** I agree. That way the backend handles authentication, file uploads, requests, and results while the ML service handles processing.

**Rahul:** Can you explain how the flow would work?

**Arjun:** Something like this: the frontend sends the input to the backend. The backend stores it and creates a processing job. The ML service picks up that job, processes the input, and generates the output. The backend then makes the result available to the frontend.

**Meera:** So the frontend doesn't directly communicate with the ML model?

**Arjun:** Exactly.

**Meera:** That makes sense.

**Karthik:** Where does the data storage fit into this?

**Arjun:** Initially we can just use local storage for development. Once we have the prototype working, we can decide whether we need cloud storage.

**Rahul:** Yes. Don't over-engineer it on Day 1.

**Ananya:** We should also make sure the architecture doesn't make us dependent on one model. If we change the model later, the rest of the application shouldn't break.

**Arjun:** That's another reason for separating the ML service.

**Rahul:** Good. So that's one architectural decision.

---

**[10:32 AM — Dataset Discussion]**

**Karthik:** I want to clarify something about the dataset. Do we need labeled data?

**Ananya:** It depends on the approach. Some parts might not require traditional labels, but we need to understand what the model expects as input and output.

**Karthik:** Okay. I'll collect different datasets rather than choosing the first one I find.

**Rahul:** How many?

**Karthik:** Maybe three to five initially. Then we can compare them.

**Ananya:** That would be useful. For each one, let's record the number of samples, image resolution, format, licensing, source, and whether there's any metadata.

**Karthik:** I'll create a comparison table.

**Meera:** Can you also include the approximate dataset size? Because if it's huge, downloading and processing it locally might be difficult.

**Karthik:** Sure.

**Rahul:** And don't spend the entire day downloading huge datasets. First check the documentation and sample data.

**Karthik:** Got it.

---

**[10:40 AM — Frontend and User Experience]**

**Meera:** I want to discuss the UI flow before I start. I'm thinking of four main screens.

**Rahul:** Go ahead.

**Meera:** First, a landing page. Second, an upload page. Third, a processing screen showing progress. And finally, a results page.

**Arjun:** That sounds good.

**Ananya:** Can the results page show some information about the generated output?

**Meera:** Yes. We can have a preview area and some basic metadata.

**Rahul:** Keep the first version simple. We don't need ten different screens.

**Meera:** Yeah, I'll make it minimal.

**Arjun:** We can give her mock JSON responses so she doesn't have to wait for my backend.

**Meera:** Perfect. That'll let me work independently.

**Rahul:** This is exactly what I want. Everyone should be able to work in parallel as much as possible.

---

**[10:46 AM — Git and Collaboration]**

**Arjun:** I'll set up the Git repository today.

**Rahul:** What branching strategy should we use?

**Arjun:** We can have `main` for stable code and individual feature branches.

**Meera:** Do we need a separate branch for every small change?

**Arjun:** Not every tiny change. But major features should have their own branches.

**Ananya:** And we'll create pull requests before merging?

**Arjun:** Yes.

**Rahul:** Let's also agree that nobody directly pushes experimental code to main.

**Everyone:** Agreed.

**Karthik:** Should we also add a README from Day 1?

**Arjun:** Definitely. I'll add setup instructions and project structure.

**Rahul:** Good. Documentation starts from Day 1, not at the end.

---

**[10:50 AM — Risks and Problems]**

**Rahul:** Let's spend a few minutes talking about what could go wrong.

**Ananya:** The biggest risk for me is the ML approach. We might find out that our initial method doesn't give good results.

**Rahul:** What will we do then?

**Ananya:** I'll keep at least two alternative approaches in mind instead of depending completely on one.

**Karthik:** Data availability is another risk. We might not find a dataset that perfectly matches our requirements.

**Rahul:** Then we can combine multiple public datasets if their formats are compatible.

**Arjun:** Backend performance could also become a problem if processing takes too long.

**Meera:** Especially if users upload large files.

**Arjun:** We can add file-size limits for the first version.

**Rahul:** Good.

**Meera:** Another issue is user experience. If processing takes ten minutes and we don't show progress, users may think the application is broken.

**Arjun:** We can handle that with background jobs.

**Rahul:** Add it to the technical tasks, but don't spend too much time optimizing before we have the basic pipeline working.

---

**[10:55 AM — Task Allocation]**

**Rahul:** Okay, let's assign today's tasks.

**Karthik:** I'll handle dataset research and analysis.

**Ananya:** I'll research the ML approaches and build a very small proof of concept.

**Arjun:** I'll create the Git repository, backend structure, API endpoints, and basic documentation.

**Meera:** I'll set up the React project and create the upload and results screens using mock data.

**Rahul:** I'll finalize the requirements, architecture diagram, task board, and coordinate everyone's work.

**Karthik:** Should we have a common deadline for these tasks?

**Rahul:** Yes. Let's aim to have the first results by the end of today.

**Meera:** Even if they're incomplete?

**Rahul:** Yes. A small working component is better than a perfect component that isn't integrated.

**Ananya:** That's fair.

---

**[11:00 AM — Defining the Day 1 Goal]**

**Rahul:** Before we finish, let's define exactly what we want by the end of Day 1.

**Arjun:** Repository should be ready.

**Meera:** Basic frontend should run.

**Karthik:** Dataset options should be identified.

**Ananya:** Initial ML approach should be tested.

**Rahul:** And we should have the architecture and task board documented.

**Meera:** Can we also try to connect the frontend to the backend today?

**Arjun:** If the basic API is ready, yes.

**Ananya:** And if my model isn't ready yet, I can provide a mock response.

**Rahul:** Perfect. That means the team can still demonstrate the complete flow even if the actual ML model isn't finished.

**Karthik:** That'll be useful for tomorrow's review.

---

**[11:05 AM — Final Discussion]**

**Rahul:** Any concerns before we close?

**Meera:** Just one. If we realize that our original idea is too complicated, are we allowed to reduce the scope?

**Rahul:** Absolutely. The goal is to build something that works. We can always add advanced features later.

**Arjun:** I think we should have a basic version first and then an advanced version.

**Ananya:** Yeah. Maybe we can define features as must-have and nice-to-have.

**Rahul:** Good idea.

**Karthik:** Must-have would be input upload, processing, and displaying the output.

**Meera:** Nice-to-have could be advanced visualization, real-time progress, and additional analysis.

**Rahul:** Exactly.

**Ananya:** That also makes it easier to explain our project during the final presentation.

**Rahul:** Good point.

**Arjun:** I'll add those categories to the task board.

**Rahul:** Great. Anything else?

**Everyone:** No.

**Rahul:** Okay, let's quickly summarize everything.

---

# Day 1 Final Decisions

1. The initial prototype will focus on **image input**.
2. Video processing will be considered for a later stage.
3. The system will have separate **frontend, backend, and ML components**.
4. React will be used for the frontend.
5. FastAPI/Python will be used for the backend.
6. Publicly available datasets will be evaluated before final selection.
7. A pretrained model will be considered before training a model from scratch.
8. Git will be used for version control.
9. Development will happen through feature branches and pull requests.
10. The first prototype will prioritize functionality over advanced features.
11. Local development will be completed before deployment is considered.
12. Features will be divided into **Must-Have** and **Nice-to-Have** categories.

---

# Day 1 Action Items

| Member      | Responsibility                                       |
| ----------- | ---------------------------------------------------- |
| **Rahul**   | Requirements, architecture, coordination, task board |
| **Ananya**  | ML research and initial prototype                    |
| **Arjun**   | Backend, APIs, Git repository                        |
| **Meera**   | Frontend and UI flow                                 |
| **Karthik** | Dataset research and preprocessing analysis          |

---

**Rahul:** If there are no other questions, let's stop here. We'll regroup tomorrow and check what everyone completed.

**Ananya:** Sounds good.

**Arjun:** Yep.

**Meera:** Works for me.

**Karthik:** Same here.

**Rahul:** Great. Day 1 done. Let's get started.

**[11:08 AM — Meeting Ended]**
