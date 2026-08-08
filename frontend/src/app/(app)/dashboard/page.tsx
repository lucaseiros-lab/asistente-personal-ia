"use client";

import { useEffect, useState } from "react";

import { PriorityBadge } from "@/components/PriorityBadge";
import { api } from "@/lib/api";
import type { EventItem, Idea, PriorityLevel, Reminder, Task } from "@/lib/types";

const PRIORITY_ORDER: PriorityLevel[] = ["rojo", "amarillo", "verde"];
const PRIORITY_LABEL: Record<PriorityLevel, string> = {
  rojo: "Acción inmediata",
  amarillo: "Preparación",
  verde: "Información",
};

function groupByPriority<T extends { priority: PriorityLevel }>(items: T[]) {
  return PRIORITY_ORDER.map((priority) => ({
    priority,
    items: items.filter((item) => item.priority === priority),
  }));
}

export default function DashboardPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.listTasks(), api.listEvents(), api.listReminders(), api.listIdeas()])
      .then(([t, e, r, i]) => {
        setTasks(t.filter((task) => task.status !== "completada" && task.status !== "cancelada"));
        setEvents(e);
        setReminders(r.filter((rem) => rem.status === "pendiente"));
        setIdeas(i);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-zinc-500">Cargando dashboard…</p>
      </div>
    );
  }

  const groupedTasks = groupByPriority(tasks);
  const groupedIdeas = groupByPriority(ideas);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-8">
      <div className="mx-auto max-w-4xl space-y-8">
        <h1 className="text-xl font-semibold text-zinc-100">Dashboard</h1>

        <section className="space-y-4">
          <h2 className="text-sm font-medium text-zinc-400">Tareas por prioridad</h2>
          {groupedTasks.every((group) => group.items.length === 0) && (
            <p className="text-sm text-zinc-500">No hay tareas pendientes.</p>
          )}
          {groupedTasks.map(
            (group) =>
              group.items.length > 0 && (
                <div key={group.priority} className="space-y-2">
                  <p className="flex items-center gap-2 text-xs uppercase tracking-wide text-zinc-500">
                    <PriorityBadge priority={group.priority} /> {PRIORITY_LABEL[group.priority]}
                  </p>
                  <ul className="space-y-1.5">
                    {group.items.map((task) => (
                      <li
                        key={task.id}
                        className="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-200"
                      >
                        {task.title}
                        {task.due_date && (
                          <span className="ml-2 text-xs text-zinc-500">
                            vence {new Date(task.due_date).toLocaleString("es-AR")}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )
          )}
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-medium text-zinc-400">Próximos eventos</h2>
          {events.length === 0 && <p className="text-sm text-zinc-500">Sin eventos próximos.</p>}
          <ul className="space-y-1.5">
            {events.map((event) => (
              <li
                key={event.id}
                className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-200"
              >
                <PriorityBadge priority={event.priority} />
                {event.title}
                <span className="ml-auto text-xs text-zinc-500">
                  {new Date(event.start_time).toLocaleString("es-AR")}
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className="space-y-2">
          <h2 className="text-sm font-medium text-zinc-400">Recordatorios</h2>
          {reminders.length === 0 && <p className="text-sm text-zinc-500">Sin recordatorios pendientes.</p>}
          <ul className="space-y-1.5">
            {reminders.map((reminder) => (
              <li
                key={reminder.id}
                className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-200"
              >
                {reminder.title}
                <span className="text-xs text-zinc-500">
                  {new Date(reminder.remind_at).toLocaleString("es-AR")}
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className="space-y-4">
          <h2 className="text-sm font-medium text-zinc-400">Ideas</h2>
          {groupedIdeas.every((group) => group.items.length === 0) && (
            <p className="text-sm text-zinc-500">Sin ideas registradas.</p>
          )}
          {groupedIdeas.map(
            (group) =>
              group.items.length > 0 && (
                <div key={group.priority} className="space-y-2">
                  <p className="flex items-center gap-2 text-xs uppercase tracking-wide text-zinc-500">
                    <PriorityBadge priority={group.priority} /> {PRIORITY_LABEL[group.priority]}
                  </p>
                  <ul className="space-y-1.5">
                    {group.items.map((idea) => (
                      <li
                        key={idea.id}
                        className="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-200"
                      >
                        {idea.title}
                      </li>
                    ))}
                  </ul>
                </div>
              )
          )}
        </section>
      </div>
    </div>
  );
}
