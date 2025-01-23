import ast
import os
import graphviz

# Configurar la ruta del ejecutable de Graphviz
os.environ["PATH"] += os.pathsep + "C:\\Program Files\\Graphviz\\bin"

class FlowchartGenerator(ast.NodeVisitor):
    def __init__(self):
        self.dot = graphviz.Digraph(comment='Flowchart')
        self.dot.attr(rankdir='TB')
        self.counter = 0
        self.stack = []
        
    def get_node_id(self):
        self.counter += 1
        return f'node_{self.counter}'
    
    def visit_FunctionDef(self, node):
        node_id = self.get_node_id()
        self.dot.node(node_id, f'Function: {node.name}')
        
        if self.stack:
            self.dot.edge(self.stack[-1], node_id)
        
        self.stack.append(node_id)
        for item in node.body:
            self.visit(item)
        self.stack.pop()
    
    def visit_If(self, node):
        node_id = self.get_node_id()
        self.dot.node(node_id, f'If: {ast.unparse(node.test)}')
        
        if self.stack:
            self.dot.edge(self.stack[-1], node_id)
        
        self.stack.append(node_id)
        for item in node.body:
            self.visit(item)
        self.stack.pop()
        
        if node.orelse:
            else_id = self.get_node_id()
            self.dot.node(else_id, 'Else')
            self.dot.edge(node_id, else_id)
            self.stack.append(else_id)
            for item in node.orelse:
                self.visit(item)
            self.stack.pop()
    
    def visit_Call(self, node):
        node_id = self.get_node_id()
        self.dot.node(node_id, f'Call: {ast.unparse(node)}')
        
        if self.stack:
            self.dot.edge(self.stack[-1], node_id)

def generate_flowchart_for_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        code = file.read()
    
    # Parsear el código Python
    tree = ast.parse(code)
    
    # Generar el flowchart
    generator = FlowchartGenerator()
    generator.visit(tree)
    
    # Obtener el nombre del archivo sin extensión
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # Crear ruta en el escritorio
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    output_path = os.path.join(desktop_path, f'flowchart_{base_name}')
    
    # Guardar el flowchart
    try:
        generator.dot.render(output_path, format='png', cleanup=True)
        print(f"Diagrama de flujo generado en: {output_path}.png")
    except Exception as e:
        print(f"Error al generar el diagrama para {file_path}: {str(e)}")

def main():
    # Lista de archivos principales para generar diagramas
    files_to_analyze = [
        'main.py',
        'ui/mainWindow.py',
        'ui/mainWindowController.py',
        'managers/chatManager.py',
        'managers/searchController.py'
    ]
    
    print("Generando diagramas de flujo...")
    for file_path in files_to_analyze:
        try:
            generate_flowchart_for_file(file_path)
        except Exception as e:
            print(f"Error al procesar {file_path}: {str(e)}")

if __name__ == '__main__':
    main() 