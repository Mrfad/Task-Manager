import flet as ft
import httpx

API_URL = "http://127.0.0.1:8000/api/v1/tasks/"  # Change if your backend uses a different URL


def main(page: ft.Page):
    page.title = "Task Manager"
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 20

    class TaskState:
        tasks = []
        next_page = None
        prev_page = None
        current_url = API_URL

    task_column = ft.Column(spacing=10, expand=True)
    pagination_row = ft.Row(spacing=10, alignment=ft.MainAxisAlignment.CENTER)

    async def load_tasks(url):
        task_column.controls.clear()
        pagination_row.controls.clear()
        page.update()

        task_column.controls.append(ft.ProgressRing())
        page.update()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                TaskState.tasks = data.get("results", [])
                TaskState.next_page = data.get("next")
                TaskState.prev_page = data.get("previous")
                TaskState.current_url = url

                task_column.controls.clear()

                for task in TaskState.tasks:
                    order_number = task.get("order_number",  "")
                    task_name = task.get("task_name", {}).get("name", "Unknown")
                    customer = task.get("customer_name", "Unknown")
                    status = task.get("status", "N/A")
                    due = task.get("job_due_date", "")
                    price = task.get("final_price", "0")
                    currency = task.get("currency", "")
                    paid = task.get("paid_status", "U")

                    task_column.controls.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column([
                                    ft.Text(order_number, size=18, weight=ft.FontWeight.BOLD),
                                    ft.Text(task_name, size=18, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"Customer: {customer}"),
                                    ft.Row([
                                        ft.Text(f"Status: {status}", expand=1),
                                        ft.Text(f"Due: {due}")
                                    ]),
                                    ft.Row([
                                        ft.Text(f"Price: {price} {currency}", expand=1),
                                        ft.Text(f"Paid: {'✅' if paid == 'P' else '❌'}")
                                    ])
                                ], spacing=4),
                                padding=15,
                                bgcolor=ft.Colors.BLUE_GREY_50,
                                border_radius=10,
                            ),
                            elevation=3,
                            margin=ft.margin.symmetric(vertical=5)
                        )
                    )

                # Pagination buttons
                if TaskState.prev_page:
                    pagination_row.controls.append(
                        ft.ElevatedButton("⬅️ Previous", on_click=lambda _: page.run_task(load_prev))
                    )
                if TaskState.next_page:
                    pagination_row.controls.append(
                        ft.ElevatedButton("Next ➡️", on_click=lambda _: page.run_task(load_next))
                    )

        except Exception as e:
            task_column.controls.clear()
            task_column.controls.append(
                ft.Text(f"❌ Error loading tasks: {e}", color=ft.Colors.RED) 
            )

        page.update()

    async def load_initial():
        await load_tasks(API_URL)

    async def load_next():
        if TaskState.next_page:
            await load_tasks(TaskState.next_page)

    async def load_prev():
        if TaskState.prev_page:
            await load_tasks(TaskState.prev_page)

    page.add(
        ft.AppBar(title=ft.Text("📋 Task Manager"), center_title=True),
        ft.Column([
            ft.ElevatedButton("🔄 Refresh", icon=ft.Icons.REFRESH, on_click=lambda _: page.run_task(load_initial)),
            task_column,
            pagination_row
        ], spacing=20)
    )

    page.run_task(load_initial)


ft.app(target=main)
