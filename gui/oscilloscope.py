import dearpygui.dearpygui as dpg
import time
import queue
import traceback

def run_dpg_process(data_queue):
    try:
        dpg.create_context()
        
        # Buffers de dados
        x_data = []
        y_data1 = [] 
        y_data2 = [] 
        
        max_points = 1000
        start_time = time.time()

        # Configuração da Janela (Primary Window)
        with dpg.window(tag="Primary Window"):
            with dpg.plot(label="Monitoramento em Tempo Real", height=-1, width=-1):
                dpg.add_plot_legend()
                
                # Eixos
                dpg.add_plot_axis(dpg.mvXAxis, label="Tempo (s)", tag="x_axis")
                with dpg.plot_axis(dpg.mvYAxis, label="Valor", tag="y_axis"):
                    
                    # Séries de dados
                    dpg.add_line_series([], [], label="Principal / Id", parent="y_axis", tag="series_1")
                    dpg.add_line_series([], [], label="Secundário / Iq", parent="y_axis", tag="series_2")
                    
                    # Aplicação de Cores (Protegido contra erros de versão)
                    try:
                        theme_1 = create_theme_color((0, 255, 255, 255)) # Ciano
                        dpg.bind_item_theme("series_1", theme_1)
                        
                        theme_2 = create_theme_color((255, 165, 0, 255)) # Laranja
                        dpg.bind_item_theme("series_2", theme_2)
                    except Exception as e:
                        print(f"Aviso: Cores padrão mantidas. Erro no tema: {e}")

        # Criação da Janela do Sistema Operacional
        # Não definimos width/height aqui pois vamos maximizar logo em seguida
        dpg.create_viewport(title="Oscilloscope MOB3")
        
        dpg.setup_dearpygui()
        
        # --- COMANDO PARA TELA CHEIA (MAXIMIZADO) ---
        #dpg.maximize_viewport() 
        # --------------------------------------------
        
        dpg.show_viewport()

        # Define a janela primária como a principal do viewport (remove bordas internas)
        dpg.set_primary_window("Primary Window", True)

        # Loop Principal
        while dpg.is_dearpygui_running():
            
            # 1. Pega o dado mais recente da fila (sem lag)
            latest_val = None
            while not data_queue.empty():
                try: latest_val = data_queue.get_nowait()
                except queue.Empty: break
            
            # 2. Processa o dado se houver
            if latest_val is not None:
                current_t = time.time() - start_time
                x_data.append(current_t)
                
                # Verifica se é Tupla (Id, Iq) ou Valor Único
                if isinstance(latest_val, (tuple, list)) and len(latest_val) >= 2:
                    id_val, iq_val = latest_val
                    y_data1.append(id_val)
                    y_data2.append(iq_val)
                    
                    dpg.configure_item("series_1", label="Corrente Id (A)")
                    dpg.configure_item("series_2", label="Corrente Iq (A)")
                else:
                    val = latest_val[0] if isinstance(latest_val, (tuple, list)) else latest_val
                    y_data1.append(val)
                    y_data2.append(0)
                    
                    dpg.configure_item("series_1", label="Valor Atual")
                    dpg.configure_item("series_2", label="")

                # Limpa buffer antigo
                if len(x_data) > max_points:
                    x_data.pop(0)
                    y_data1.pop(0)
                    y_data2.pop(0)

                # Atualiza Gráfico
                dpg.set_value("series_1", [x_data, y_data1])
                
                if isinstance(latest_val, (tuple, list)) and len(latest_val) >= 2:
                    dpg.set_value("series_2", [x_data, y_data2])
                else:
                    dpg.set_value("series_2", [[], []]) 

                # Auto-fit nos eixos
                dpg.fit_axis_data("x_axis")
                dpg.fit_axis_data("y_axis")

            dpg.render_dearpygui_frame()

        dpg.destroy_context()
        
    except Exception as e:
        print("ERRO NO OSCILOSCÓPIO:")
        traceback.print_exc()

def create_theme_color(color):
    with dpg.theme() as theme:
        # Usamos mvAll para evitar o erro "Style target out of range"
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_PlotLines, color, category=dpg.mvThemeCat_Plots)
    return theme