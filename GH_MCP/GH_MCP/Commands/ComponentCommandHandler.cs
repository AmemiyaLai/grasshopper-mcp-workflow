using System;
using System.Collections.Generic;
using GrasshopperMCP.Models;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Parameters;
using Grasshopper.Kernel.Special;
using Rhino;
using Rhino.Geometry;
using Grasshopper;
using System.Linq;
using Grasshopper.Kernel.Components;
using System.Threading;
using GH_MCP.Utils;

namespace GrasshopperMCP.Commands
{
    /// <summary>
    /// 處理組件相關命令的處理器
    /// </summary>
    public static class ComponentCommandHandler
    {
        /// <summary>
        /// 添加組件
        /// </summary>
        /// <param name="command">包含組件類型和位置的命令</param>
        /// <returns>添加的組件信息</returns>
        public static object AddComponent(Command command)
        {
            string type = command.GetParameter<string>("type");
            double x = command.GetParameter<double>("x");
            double y = command.GetParameter<double>("y");
            
            // 可選參數：用於區分同名組件
            string category = command.GetParameter<string>("category");
            string guid = command.GetParameter<string>("guid");
            string library = command.GetParameter<string>("library");
            

            if (string.IsNullOrEmpty(type))
            {
                throw new ArgumentException("Component type is required");
            }
            
            // 使用模糊匹配獲取標準化的元件名稱
            string normalizedType = FuzzyMatcher.GetClosestComponentName(type);
            
            // 記錄請求信息
            RhinoApp.WriteLine($"AddComponent request: type={type}, normalized={normalizedType}, x={x}, y={y}, category={category}, guid={guid}, library={library}");
            
            object result = null;
            Exception exception = null;
            
            // 在 UI 線程上執行
            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    // 獲取 Grasshopper 文檔
                    var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        throw new InvalidOperationException("No active Grasshopper document");
                    }
                    
                    // 創建組件
                    IGH_DocumentObject component = null;
                    
                    // 記錄可用的組件類型（僅在第一次調用時記錄）
                    bool loggedComponentTypes = false;
                    if (!loggedComponentTypes)
                    {
                        var availableTypes = Grasshopper.Instances.ComponentServer.ObjectProxies
                            .Select(p => p.Desc.Name)
                            .OrderBy(n => n)
                            .ToList();
                        
                        RhinoApp.WriteLine($"Available component types: {string.Join(", ", availableTypes.Take(50))}...");
                        loggedComponentTypes = true;
                    }
                    
                    // 根據類型創建不同的組件
                    switch (normalizedType.ToLowerInvariant())
                    {
                        // 平面元件
                        case "xy plane":
                            component = CreateComponentByName("XY Plane");
                            break;
                        case "xz plane":
                            component = CreateComponentByName("XZ Plane");
                            break;
                        case "yz plane":
                            component = CreateComponentByName("YZ Plane");
                            break;
                        case "plane 3pt":
                            component = CreateComponentByName("Plane 3Pt");
                            break;
                            
                        // 基本幾何元件
                        case "box":
                            component = CreateComponentByName("Box");
                            break;
                        case "sphere":
                            component = CreateComponentByName("Sphere");
                            break;
                        case "cylinder":
                            component = CreateComponentByName("Cylinder");
                            break;
                        case "cone":
                            component = CreateComponentByName("Cone");
                            break;
                        case "circle":
                            component = CreateComponentByName("Circle");
                            break;
                        case "rectangle":
                            component = CreateComponentByName("Rectangle");
                            break;
                        case "line":
                            component = CreateComponentByName("Line");
                            break;
                            
                        // 參數元件
                        case "point":
                        case "pt":
                        case "pointparam":
                        case "param_point":
                            component = new Param_Point();
                            break;
                        case "curve":
                        case "crv":
                        case "curveparam":
                        case "param_curve":
                            component = new Param_Curve();
                            break;
                        case "circleparam":
                        case "param_circle":
                            component = new Param_Circle();
                            break;
                        case "lineparam":
                        case "param_line":
                            component = new Param_Line();
                            break;
                        case "panel":
                        case "gh_panel":
                            component = new GH_Panel();
                            break;
                        case "slider":
                        case "numberslider":
                        case "gh_numberslider":
                            var slider = new GH_NumberSlider();
                            slider.SetInitCode("0.0 < 0.5 < 1.0");
                            component = slider;
                            break;
                        case "number":
                        case "num":
                        case "integer":
                        case "int":
                        case "param_number":
                        case "param_integer":
                            component = new Param_Number();
                            break;
                        case "construct point":
                        case "constructpoint":
                        case "pt xyz":
                        case "xyz":
                            // 嘗試查找構造點組件
                            var pointProxy = Grasshopper.Instances.ComponentServer.ObjectProxies
                                .FirstOrDefault(p => p.Desc.Name.Equals("Construct Point", StringComparison.OrdinalIgnoreCase));
                            if (pointProxy != null)
                            {
                                component = pointProxy.CreateInstance();
                            }
                            else
                            {
                                throw new ArgumentException("Construct Point component not found");
                            }
                            break;
                        default:
                            // 嘗試通過 Guid 查找組件
                            Guid componentGuid;
                            if (Guid.TryParse(type, out componentGuid))
                            {
                                component = Grasshopper.Instances.ComponentServer.EmitObject(componentGuid);
                                RhinoApp.WriteLine($"Attempting to create component by GUID: {componentGuid}");
                            }
                            
                            if (component == null)
                            {
                                // 嘗試通過名稱查找組件（不區分大小寫）
                                RhinoApp.WriteLine($"Attempting to find component by name: {type}");
                                
                                // 獲取所有匹配的組件
                                var matchingProxies = Grasshopper.Instances.ComponentServer.ObjectProxies
                                    .Where(p => p.Desc.Name.Equals(type, StringComparison.OrdinalIgnoreCase))
                                    .ToList();
                                
                                if (matchingProxies.Count == 0)
                                {
                                    // 嘗試通過部分名稱匹配
                                    RhinoApp.WriteLine($"Attempting to find component by partial name match: {type}");
                                    matchingProxies = Grasshopper.Instances.ComponentServer.ObjectProxies
                                        .Where(p => p.Desc.Name.IndexOf(type, StringComparison.OrdinalIgnoreCase) >= 0)
                                        .ToList();
                                }
                                
                                if (matchingProxies.Count == 0)
                                {
                                    // 沒有找到任何匹配
                                    var possibleMatches = Grasshopper.Instances.ComponentServer.ObjectProxies
                                        .Where(p => p.Desc.Name.IndexOf(type, StringComparison.OrdinalIgnoreCase) >= 0)
                                        .Select(p => p.Desc.Name)
                                        .Take(10)
                                        .ToList();
                                    
                                    var errorMessage = $"Unknown component type: {type}";
                                    if (possibleMatches.Any())
                                    {
                                        errorMessage += $". Possible matches: {string.Join(", ", possibleMatches)}";
                                    }
                                    
                                    throw new ArgumentException(errorMessage);
                                }
                                else if (matchingProxies.Count == 1)
                                {
                                    // 只有一個匹配，直接使用
                                    var obj = matchingProxies[0];
                                    RhinoApp.WriteLine($"Found component: {obj.Desc.Name} (GUID: {obj.Desc.InstanceGuid})");
                                    component = obj.CreateInstance();
                                }
                                else
                                {
                                    // 有多個同名組件，嘗試使用額外參數來區分
                                    RhinoApp.WriteLine($"Found {matchingProxies.Count} components with name '{type}'. Attempting to filter by additional parameters...");
                                    
                                    var filteredProxies = matchingProxies;
                                    
                                    // 如果提供了 GUID，優先使用 GUID 匹配
                                    if (!string.IsNullOrEmpty(guid))
                                    {
                                        Guid requestedGuid;
                                        if (Guid.TryParse(guid, out requestedGuid))
                                        {
                                            filteredProxies = filteredProxies
                                                .Where(p => p.Desc.InstanceGuid == requestedGuid)
                                                .ToList();
                                            
                                            if (filteredProxies.Count > 0)
                                            {
                                                RhinoApp.WriteLine($"Filtered by GUID: {requestedGuid}");
                                            }
                                        }
                                    }
                                    
                                    // 如果提供了 category，使用 category 過濾
                                    if (filteredProxies.Count > 1 && !string.IsNullOrEmpty(category))
                                    {
                                        filteredProxies = filteredProxies
                                            .Where(p => p.Desc.Category != null && 
                                                       p.Desc.Category.Equals(category, StringComparison.OrdinalIgnoreCase))
                                            .ToList();
                                        
                                        if (filteredProxies.Count > 0)
                                        {
                                            RhinoApp.WriteLine($"Filtered by category: {category}");
                                        }
                                    }
                                    
                                    // 如果提供了 library，使用 library 過濾
                                    if (filteredProxies.Count > 1 && !string.IsNullOrEmpty(library))
                                    {
                                        filteredProxies = filteredProxies
                                            .Where(p => 
                                            {
                                                try
                                                {
                                                    // 嘗試從組件實例獲取庫信息
                                                    var tempComp = p.CreateInstance();
                                                    if (tempComp != null)
                                                    {
                                                        var libName = tempComp.GetType().Assembly.GetName().Name;
                                                        return libName != null && libName.IndexOf(library, StringComparison.OrdinalIgnoreCase) >= 0;
                                                    }
                                                }
                                                catch { }
                                                return false;
                                            })
                                            .ToList();
                                        
                                        if (filteredProxies.Count > 0)
                                        {
                                            RhinoApp.WriteLine($"Filtered by library: {library}");
                                        }
                                    }
                                    
                                    // 智能選擇：如果沒有明確指定，優先選擇未廢棄的原生內建組件
                                    if (filteredProxies.Count > 1 && string.IsNullOrEmpty(guid))
                                    {
                                        // 首先排除廢棄的組件（通過檢查組件類型名稱或創建實例）
                                        var nonObsolete = new List<Grasshopper.Kernel.IGH_ObjectProxy>();
                                        foreach (var proxy in filteredProxies)
                                        {
                                            try
                                            {
                                                var tempComp = proxy.CreateInstance();
                                                // 檢查組件類型名稱是否包含 "Obsolete" 或 "Deprecated"
                                                var typeName = tempComp.GetType().Name;
                                                if (typeName.IndexOf("Obsolete", StringComparison.OrdinalIgnoreCase) < 0 &&
                                                    typeName.IndexOf("Deprecated", StringComparison.OrdinalIgnoreCase) < 0)
                                                {
                                                    nonObsolete.Add(proxy);
                                                }
                                            }
                                            catch
                                            {
                                                // 如果無法創建，假設不是廢棄的
                                                nonObsolete.Add(proxy);
                                            }
                                        }
                                        
                                        if (nonObsolete.Count > 0)
                                        {
                                            filteredProxies = nonObsolete;
                                            RhinoApp.WriteLine($"Filtered out obsolete components. {filteredProxies.Count} non-obsolete components remaining.");
                                        }
                                        
                                        // 如果仍然有多個，優先選擇原生內建組件（通過檢查 Assembly 名稱）
                                        if (filteredProxies.Count > 1)
                                        {
                                            var builtIn = new List<Grasshopper.Kernel.IGH_ObjectProxy>();
                                            foreach (var proxy in filteredProxies)
                                            {
                                                try
                                                {
                                                    var tempComp = proxy.CreateInstance();
                                                    var assemblyName = tempComp.GetType().Assembly.GetName().Name;
                                                    if (assemblyName != null && 
                                                        (assemblyName.Equals("Grasshopper", StringComparison.OrdinalIgnoreCase) ||
                                                         assemblyName.IndexOf("Grasshopper", StringComparison.OrdinalIgnoreCase) >= 0))
                                                    {
                                                        builtIn.Add(proxy);
                                                    }
                                                }
                                                catch { }
                                            }
                                            
                                            if (builtIn.Count > 0)
                                            {
                                                filteredProxies = builtIn;
                                                RhinoApp.WriteLine($"Prioritized built-in Grasshopper components. {filteredProxies.Count} built-in components remaining.");
                                            }
                                        }
                                        
                                        // 如果仍然有多個，選擇第一個（通常是最常用的）
                                        if (filteredProxies.Count > 1)
                                        {
                                            RhinoApp.WriteLine($"Multiple components still match. Using the first one: {filteredProxies[0].Desc.Name} (GUID: {filteredProxies[0].Desc.InstanceGuid})");
                                            filteredProxies = filteredProxies.Take(1).ToList();
                                        }
                                    }
                                    
                                    if (filteredProxies.Count == 0)
                                    {
                                        // 過濾後沒有匹配，返回所有候選項的信息（包含詳細信息）
                                        var candidates = matchingProxies.Select(p => 
                                        {
                                            // 嘗試創建臨時實例以獲取輸入輸出信息
                                            IGH_DocumentObject tempComponent = null;
                                            List<object> inputs = null;
                                            List<object> outputs = null;
                                            string libraryName = "Unknown";
                                            bool isObsolete = false;
                                            bool isBuiltIn = false;
                                            string description = "No description available";
                                            
                                            try
                                            {
                                                tempComponent = p.CreateInstance();
                                                
                                                // 獲取庫名稱
                                                try
                                                {
                                                    libraryName = tempComponent.GetType().Assembly.GetName().Name ?? "Unknown";
                                                    isBuiltIn = libraryName.Equals("Grasshopper", StringComparison.OrdinalIgnoreCase) ||
                                                               libraryName.IndexOf("Grasshopper", StringComparison.OrdinalIgnoreCase) >= 0;
                                                }
                                                catch { }
                                                
                                                // 檢查是否廢棄
                                                try
                                                {
                                                    var typeName = tempComponent.GetType().Name;
                                                    isObsolete = typeName.Contains("Obsolete", StringComparison.OrdinalIgnoreCase) ||
                                                                typeName.Contains("Deprecated", StringComparison.OrdinalIgnoreCase);
                                                }
                                                catch { }
                                                
                                                // 獲取描述
                                                try
                                                {
                                                    description = tempComponent.Description ?? "No description available";
                                                }
                                                catch { }
                                                
                                                if (tempComponent is IGH_Component comp)
                                                {
                                                    inputs = comp.Params.Input.Select(ip => new
                                                    {
                                                        name = ip.Name,
                                                        nickname = ip.NickName,
                                                        type = ip.TypeName,
                                                        description = ip.Description
                                                    }).Cast<object>().ToList();
                                                    
                                                    outputs = comp.Params.Output.Select(op => new
                                                    {
                                                        name = op.Name,
                                                        nickname = op.NickName,
                                                        type = op.TypeName,
                                                        description = op.Description
                                                    }).Cast<object>().ToList();
                                                }
                                            }
                                            catch
                                            {
                                                // 如果無法創建實例，使用默認值
                                            }
                                            
                                            return new
                                            {
                                                name = p.Desc.Name,
                                                guid = p.Desc.InstanceGuid.ToString(),
                                                category = p.Desc.Category?.ToString() ?? "Unknown",
                                                subCategory = p.Desc.SubCategory?.ToString() ?? "Unknown",
                                                library = libraryName,
                                                description = description,
                                                obsolete = isObsolete,
                                                isBuiltIn = isBuiltIn,
                                                inputs = inputs,
                                                outputs = outputs
                                            };
                                        }).ToList();
                                        
                                        var errorMessage = $"Multiple components found with name '{type}' but none match the specified filters (category={category}, guid={guid}, library={library}). " +
                                                          $"Available candidates:\n" +
                                                          string.Join("\n", candidates.Select(c => 
                                                              $"  - {c.name} (GUID: {c.guid})\n" +
                                                              $"    Category: {c.category}, SubCategory: {c.subCategory}\n" +
                                                              $"    Library: {c.library} {(c.isBuiltIn ? "(Built-in)" : "")}\n" +
                                                              $"    Obsolete: {(c.obsolete ? "Yes" : "No")}\n" +
                                                              $"    Description: {c.description}\n" +
                                                              (c.inputs != null && c.inputs.Count > 0 ? 
                                                                  $"    Inputs: {string.Join(", ", c.inputs.Cast<dynamic>().Select(i => $"{i.name} ({i.type})"))}\n" : "") +
                                                              (c.outputs != null && c.outputs.Count > 0 ? 
                                                                  $"    Outputs: {string.Join(", ", c.outputs.Cast<dynamic>().Select(o => $"{o.name} ({o.type})"))}\n" : "")));
                                        
                                        throw new ArgumentException(errorMessage);
                                    }
                                    else if (filteredProxies.Count == 1)
                                    {
                                        // 過濾後只有一個匹配
                                        var obj = filteredProxies[0];
                                        RhinoApp.WriteLine($"Found component after filtering: {obj.Desc.Name} (GUID: {obj.Desc.InstanceGuid})");
                                        component = obj.CreateInstance();
                                    }
                                    else
                                    {
                                        // 過濾後仍然有多個匹配，返回候選項信息（包含詳細信息）
                                        var candidates = filteredProxies.Select(p => 
                                        {
                                            // 嘗試創建臨時實例以獲取輸入輸出信息
                                            IGH_DocumentObject tempComponent = null;
                                            List<object> inputs = null;
                                            List<object> outputs = null;
                                            string libraryName = "Unknown";
                                            bool isObsolete = false;
                                            bool isBuiltIn = false;
                                            string description = "No description available";
                                            
                                            try
                                            {
                                                tempComponent = p.CreateInstance();
                                                
                                                // 獲取庫名稱
                                                try
                                                {
                                                    libraryName = tempComponent.GetType().Assembly.GetName().Name ?? "Unknown";
                                                    isBuiltIn = libraryName.Equals("Grasshopper", StringComparison.OrdinalIgnoreCase) ||
                                                               libraryName.IndexOf("Grasshopper", StringComparison.OrdinalIgnoreCase) >= 0;
                                                }
                                                catch { }
                                                
                                                // 檢查是否廢棄
                                                try
                                                {
                                                    var typeName = tempComponent.GetType().Name;
                                                    isObsolete = typeName.Contains("Obsolete", StringComparison.OrdinalIgnoreCase) ||
                                                                typeName.Contains("Deprecated", StringComparison.OrdinalIgnoreCase);
                                                }
                                                catch { }
                                                
                                                // 獲取描述
                                                try
                                                {
                                                    description = tempComponent.Description ?? "No description available";
                                                }
                                                catch { }
                                                
                                                if (tempComponent is IGH_Component comp)
                                                {
                                                    inputs = comp.Params.Input.Select(ip => new
                                                    {
                                                        name = ip.Name,
                                                        nickname = ip.NickName,
                                                        type = ip.TypeName,
                                                        description = ip.Description
                                                    }).Cast<object>().ToList();
                                                    
                                                    outputs = comp.Params.Output.Select(op => new
                                                    {
                                                        name = op.Name,
                                                        nickname = op.NickName,
                                                        type = op.TypeName,
                                                        description = op.Description
                                                    }).Cast<object>().ToList();
                                                }
                                            }
                                            catch
                                            {
                                                // 如果無法創建實例，使用默認值
                                            }
                                            
                                            return new
                                            {
                                                name = p.Desc.Name,
                                                guid = p.Desc.InstanceGuid.ToString(),
                                                category = p.Desc.Category?.ToString() ?? "Unknown",
                                                subCategory = p.Desc.SubCategory?.ToString() ?? "Unknown",
                                                library = libraryName,
                                                description = description,
                                                obsolete = isObsolete,
                                                isBuiltIn = isBuiltIn,
                                                inputs = inputs,
                                                outputs = outputs
                                            };
                                        }).ToList();
                                        
                                        var errorMessage = $"Multiple components found with name '{type}' ({filteredProxies.Count} matches). " +
                                                          $"Please specify additional parameters (guid, category, or library) to distinguish. " +
                                                          $"Recommendation: Prefer non-obsolete, built-in components.\n" +
                                                          $"Available candidates:\n" +
                                                          string.Join("\n", candidates.Select(c => 
                                                              $"  - {c.name} (GUID: {c.guid})\n" +
                                                              $"    Category: {c.category}, SubCategory: {c.subCategory}\n" +
                                                              $"    Library: {c.library} {(c.isBuiltIn ? "(Built-in - Recommended)" : "")}\n" +
                                                              $"    Obsolete: {(c.obsolete ? "Yes (Not Recommended)" : "No (Recommended)")}\n" +
                                                              $"    Description: {c.description}\n" +
                                                              (c.inputs != null && c.inputs.Count > 0 ? 
                                                                  $"    Inputs: {string.Join(", ", c.inputs.Cast<dynamic>().Select(i => $"{i.name} ({i.type})"))}\n" : "") +
                                                              (c.outputs != null && c.outputs.Count > 0 ? 
                                                                  $"    Outputs: {string.Join(", ", c.outputs.Cast<dynamic>().Select(o => $"{o.name} ({o.type})"))}\n" : "")));
                                        
                                        throw new ArgumentException(errorMessage);
                                    }
                                }
                            }
                            break;
                    }
                    
                    // 設置組件位置
                    if (component != null)
                    {
                        // 確保組件有有效的屬性對象
                        if (component.Attributes == null)
                        {
                            RhinoApp.WriteLine("Component attributes are null, creating new attributes");
                            component.CreateAttributes();
                        }
                        
                        // 設置位置
                        component.Attributes.Pivot = new System.Drawing.PointF((float)x, (float)y);
                        
                        // 添加到文檔
                        doc.AddObject(component, false);
                        
                        // 刷新畫布
                        doc.NewSolution(false);
                        
                        // 返回組件信息
                        result = new
                        {
                            id = component.InstanceGuid.ToString(),
                            type = component.GetType().Name,
                            name = component.NickName,
                            x = component.Attributes.Pivot.X,
                            y = component.Attributes.Pivot.Y
                        };
                    }
                    else
                    {
                        throw new InvalidOperationException("Failed to create component");
                    }
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in AddComponent: {ex.Message}");
                }
            }));
            
            // 等待 UI 線程操作完成
            while (result == null && exception == null)
            {
                Thread.Sleep(10);
            }
            
            // 如果有異常，拋出
            if (exception != null)
            {
                throw exception;
            }
            
            return result;
        }
        
        /// <summary>
        /// 連接組件
        /// </summary>
        /// <param name="command">包含源和目標組件信息的命令</param>
        /// <returns>連接信息</returns>
        public static object ConnectComponents(Command command)
        {
            var fromData = command.GetParameter<Dictionary<string, object>>("from");
            var toData = command.GetParameter<Dictionary<string, object>>("to");
            
            if (fromData == null || toData == null)
            {
                throw new ArgumentException("Source and target component information are required");
            }
            
            object result = null;
            Exception exception = null;
            
            // 在 UI 線程上執行
            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    // 獲取 Grasshopper 文檔
                    var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        throw new InvalidOperationException("No active Grasshopper document");
                    }
                    
                    // 解析源組件信息
                    string fromIdStr = fromData["id"].ToString();
                    string fromParamName = fromData["parameterName"].ToString();
                    
                    // 解析目標組件信息
                    string toIdStr = toData["id"].ToString();
                    string toParamName = toData["parameterName"].ToString();
                    
                    // 將字符串 ID 轉換為 Guid
                    Guid fromId, toId;
                    if (!Guid.TryParse(fromIdStr, out fromId) || !Guid.TryParse(toIdStr, out toId))
                    {
                        throw new ArgumentException("Invalid component ID format");
                    }
                    
                    // 查找源和目標組件
                    IGH_Component fromComponent = doc.FindComponent(fromId) as IGH_Component;
                    IGH_Component toComponent = doc.FindComponent(toId) as IGH_Component;
                    
                    if (fromComponent == null || toComponent == null)
                    {
                        throw new ArgumentException("Source or target component not found");
                    }
                    
                    // 查找源輸出參數
                    IGH_Param fromParam = null;
                    foreach (var param in fromComponent.Params.Output)
                    {
                        if (param.Name.Equals(fromParamName, StringComparison.OrdinalIgnoreCase))
                        {
                            fromParam = param;
                            break;
                        }
                    }
                    
                    // 查找目標輸入參數
                    IGH_Param toParam = null;
                    foreach (var param in toComponent.Params.Input)
                    {
                        if (param.Name.Equals(toParamName, StringComparison.OrdinalIgnoreCase))
                        {
                            toParam = param;
                            break;
                        }
                    }
                    
                    if (fromParam == null || toParam == null)
                    {
                        throw new ArgumentException("Source or target parameter not found");
                    }
                    
                    // 連接參數
                    toParam.AddSource(fromParam);
                    
                    // 刷新畫布
                    doc.NewSolution(false);
                    
                    // 返回連接信息
                    result = new
                    {
                        from = new
                        {
                            id = fromComponent.InstanceGuid.ToString(),
                            name = fromComponent.NickName,
                            parameter = fromParam.Name
                        },
                        to = new
                        {
                            id = toComponent.InstanceGuid.ToString(),
                            name = toComponent.NickName,
                            parameter = toParam.Name
                        }
                    };
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in ConnectComponents: {ex.Message}");
                }
            }));
            
            // 等待 UI 線程操作完成
            while (result == null && exception == null)
            {
                Thread.Sleep(10);
            }
            
            // 如果有異常，拋出
            if (exception != null)
            {
                throw exception;
            }
            
            return result;
        }
        
        /// <summary>
        /// 設置組件值
        /// </summary>
        /// <param name="command">包含組件 ID 和值的命令</param>
        /// <returns>操作結果</returns>
        public static object SetComponentValue(Command command)
        {
            string idStr = command.GetParameter<string>("id");
            string value = command.GetParameter<string>("value");
            
            if (string.IsNullOrEmpty(idStr))
            {
                throw new ArgumentException("Component ID is required");
            }
            
            object result = null;
            Exception exception = null;
            
            // 在 UI 線程上執行
            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    // 獲取 Grasshopper 文檔
                    var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        throw new InvalidOperationException("No active Grasshopper document");
                    }
                    
                    // 將字符串 ID 轉換為 Guid
                    Guid id;
                    if (!Guid.TryParse(idStr, out id))
                    {
                        throw new ArgumentException("Invalid component ID format");
                    }
                    
                    // 查找組件
                    IGH_DocumentObject component = doc.FindObject(id, true);
                    if (component == null)
                    {
                        throw new ArgumentException($"Component with ID {idStr} not found");
                    }
                    
                    // 根據組件類型設置值
                    if (component is GH_Panel panel)
                    {
                        panel.UserText = value;
                    }
                    else if (component is GH_NumberSlider slider)
                    {
                        double doubleValue;
                        if (double.TryParse(value, out doubleValue))
                        {
                            slider.SetSliderValue((decimal)doubleValue);
                        }
                        else
                        {
                            throw new ArgumentException("Invalid slider value format");
                        }
                    }
                    else if (component is IGH_Component ghComponent)
                    {
                        // 嘗試設置第一個輸入參數的值
                        if (ghComponent.Params.Input.Count > 0)
                        {
                            var param = ghComponent.Params.Input[0];
                            if (param is Param_String stringParam)
                            {
                                stringParam.PersistentData.Clear();
                                stringParam.PersistentData.Append(new Grasshopper.Kernel.Types.GH_String(value));
                            }
                            else if (param is Param_Number numberParam)
                            {
                                double doubleValue;
                                if (double.TryParse(value, out doubleValue))
                                {
                                    numberParam.PersistentData.Clear();
                                    numberParam.PersistentData.Append(new Grasshopper.Kernel.Types.GH_Number(doubleValue));
                                }
                                else
                                {
                                    throw new ArgumentException("Invalid number value format");
                                }
                            }
                            else
                            {
                                throw new ArgumentException($"Cannot set value for parameter type {param.GetType().Name}");
                            }
                        }
                        else
                        {
                            throw new ArgumentException("Component has no input parameters");
                        }
                    }
                    else
                    {
                        throw new ArgumentException($"Cannot set value for component type {component.GetType().Name}");
                    }
                    
                    // 刷新畫布
                    doc.NewSolution(false);
                    
                    // 返回操作結果
                    result = new
                    {
                        id = component.InstanceGuid.ToString(),
                        type = component.GetType().Name,
                        value = value
                    };
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in SetComponentValue: {ex.Message}");
                }
            }));
            
            // 等待 UI 線程操作完成
            while (result == null && exception == null)
            {
                Thread.Sleep(10);
            }
            
            // 如果有異常，拋出
            if (exception != null)
            {
                throw exception;
            }
            
            return result;
        }
        
        /// <summary>
        /// 獲取組件信息
        /// </summary>
        /// <param name="command">包含組件 ID 的命令</param>
        /// <returns>組件信息</returns>
        public static object GetComponentInfo(Command command)
        {
            string idStr = command.GetParameter<string>("id");
            
            if (string.IsNullOrEmpty(idStr))
            {
                throw new ArgumentException("Component ID is required");
            }
            
            object result = null;
            Exception exception = null;
            
            // 在 UI 線程上執行
            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    // 獲取 Grasshopper 文檔
                    var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        throw new InvalidOperationException("No active Grasshopper document");
                    }
                    
                    // 將字符串 ID 轉換為 Guid
                    Guid id;
                    if (!Guid.TryParse(idStr, out id))
                    {
                        throw new ArgumentException("Invalid component ID format");
                    }
                    
                    // 查找組件
                    IGH_DocumentObject component = doc.FindObject(id, true);
                    if (component == null)
                    {
                        throw new ArgumentException($"Component with ID {idStr} not found");
                    }
                    
                    // 收集組件信息
                    var componentInfo = new Dictionary<string, object>
                    {
                        { "id", component.InstanceGuid.ToString() },
                        { "type", component.GetType().Name },
                        { "name", component.NickName },
                        { "description", component.Description }
                    };
                    
                    // 如果是 IGH_Component，收集輸入和輸出參數信息
                    if (component is IGH_Component ghComponent)
                    {
                        var inputs = new List<Dictionary<string, object>>();
                        foreach (var param in ghComponent.Params.Input)
                        {
                            inputs.Add(new Dictionary<string, object>
                            {
                                { "name", param.Name },
                                { "nickname", param.NickName },
                                { "description", param.Description },
                                { "type", param.GetType().Name },
                                { "dataType", param.TypeName }
                            });
                        }
                        componentInfo["inputs"] = inputs;
                        
                        var outputs = new List<Dictionary<string, object>>();
                        foreach (var param in ghComponent.Params.Output)
                        {
                            outputs.Add(new Dictionary<string, object>
                            {
                                { "name", param.Name },
                                { "nickname", param.NickName },
                                { "description", param.Description },
                                { "type", param.GetType().Name },
                                { "dataType", param.TypeName }
                            });
                        }
                        componentInfo["outputs"] = outputs;
                    }
                    
                    // 如果是 GH_Panel，獲取其文本值
                    if (component is GH_Panel panel)
                    {
                        componentInfo["value"] = panel.UserText;
                    }
                    
                    // 如果是 GH_NumberSlider，獲取其值和範圍
                    if (component is GH_NumberSlider slider)
                    {
                        componentInfo["value"] = (double)slider.CurrentValue;
                        componentInfo["minimum"] = (double)slider.Slider.Minimum;
                        componentInfo["maximum"] = (double)slider.Slider.Maximum;
                    }
                    
                    result = componentInfo;
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in GetComponentInfo: {ex.Message}");
                }
            }));
            
            // 等待 UI 線程操作完成
            while (result == null && exception == null)
            {
                Thread.Sleep(10);
            }
            
            // 如果有異常，拋出
            if (exception != null)
            {
                throw exception;
            }
            
            return result;
        }
        
        private static IGH_DocumentObject CreateComponentByName(string name)
        {
            var obj = Grasshopper.Instances.ComponentServer.ObjectProxies
                .FirstOrDefault(p => p.Desc.Name.Equals(name, StringComparison.OrdinalIgnoreCase));
                
            if (obj != null)
            {
                return obj.CreateInstance();
            }
            else
            {
                throw new ArgumentException($"Component with name {name} not found");
            }
        }
    }
}
