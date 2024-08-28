import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { JsonForms } from '@jsonforms/react';
import { materialRenderers, materialCells } from '@jsonforms/material-renderers';
import * as XLSX from 'xlsx';
import { openDB } from 'idb';
import { 
  PerformingTroupesRenderer, 
  PerformanceCastsRenderer,
  PerformanceWorksRenderer,
  CastDescriptionRenderer,
  CustomTextAreaControl
} from './CustomRenderers';
import { Button, Box, TextField, Typography, Container, Grid, Paper, Select, MenuItem, InputLabel, FormControl } from '@mui/material';
import ArrowBackIosNewIcon from '@mui/icons-material/ArrowBackIosNew';
import ArrowForwardIosIcon from '@mui/icons-material/ArrowForwardIos';
import { MaterialTableControl } from '@jsonforms/material-renderers';

interface ExcelRow {
  [key: string]: any;
  createdAt?: string;
  updatedAt?: string;
}

interface JsonData {
  performingEvents?: Array<{
    name: string;
    description?: string;
    sectionsOrActs: string;
    createdAt?: string;
    updatedAt?: string;
    castDescription?: {
      description: string;
      performanceResponsibilities: Array<{
        performerName: string;
        responsibility: string;
        characterName?: string;
      }>;
    };
  }>;
  [key: string]: any;
}



const generateSchema = (data: any): any => {
  if (data === null) {
    return { type: 'null' };
  }

  if (Array.isArray(data)) {
    return {
      type: 'array',
      items: data.length > 0 ? generateSchema(data[0]) : {}
    };
  }

  if (typeof data === 'object') {
    const properties: { [key: string]: any } = {};
    const required: string[] = [];

    Object.keys(data).forEach(key => {
      if (key !== 'metadata' && !key.startsWith('metadata_')) {
        if (key === 'eventType' && data[key] && typeof data[key] === 'object') {
          properties[key] = {
            type: 'object',
            properties: {
              type: {
                type: 'string',
                enum: ['戏曲演出', '戏剧演出', '音乐节'] // 添加所有可能的选项
              }
            },
            required: ['type']
          };
        } else if (key === 'description') {
          properties[key] = {
            type: 'string',
            format: 'textarea'
          };
        } else {
          properties[key] = generateSchema(data[key]);
        }
        if (data[key] !== undefined) {
          required.push(key);
        }
      }
    });

    return {
      type: 'object',
      properties,
      required: required.length > 0 ? required : undefined
    };
  }

  // 处理基本类型
  const type = typeof data;
  if (type === 'string' || type === 'number' || type === 'boolean') {
    return { type };
  }

  // 如果是其他类型，返回一个通用的 schema
  return {};
};


const customRenderers = [
  ...materialRenderers,
  { tester: (schema) => schema.type === 'array' && schema.items.properties?.name && schema.items.properties?.role ? 10 : -1, renderer: PerformingTroupesRenderer },
  { tester: (schema) => schema.type === 'array' && schema.items.properties?.name && schema.items.properties?.sectionsOrActs ? 10 : -1, renderer: PerformanceWorksRenderer },
  { tester: (schema) => schema.type === 'array' && schema.items.properties?.name && schema.items.properties?.role && !schema.items.properties?.description ? 10 : -1, renderer: PerformanceCastsRenderer },
  { tester: (schema) => schema.type === 'object' && schema.properties?.description && schema.properties?.performanceResponsibilities ? 10 : -1, renderer: CastDescriptionRenderer },
  { 
    tester: (schema, uischema) => 
      uischema.type === 'Control' && 
      schema.type === 'string' && 
      (schema.format === 'textarea' || uischema.options?.multiline),
    renderer: CustomTextAreaControl
  },
  { tester: () => 1, renderer: (props) => <div>无法渲染此类型的数据</div> }
];


const ExcelJsonEditor: React.FC = () => {
  console.log('ExcelJsonEditor is rendering');
  const [excelData, setExcelData] = useState<ExcelRow[]>([]);
  const [currentRow, setCurrentRow] = useState<number | null>(null);
  const [jsonData, setJsonData] = useState<JsonData>({});
  const [schema, setSchema] = useState<any>({});
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isDataLoaded, setIsDataLoaded] = useState<boolean>(false);
  const [isInitializing, setIsInitializing] = useState(true);

  const jsonColumnName = '演出类型';
  const editedColumnName = '人工编辑';


  console.log('Rendering ExcelJsonEditor. ExcelData:', excelData);
  console.log('Current row:', currentRow);
  console.log('JSON data:', jsonData);

  const loadDataFromIndexedDB = useCallback(async () => {
    try {
      const db = await openDB('excelDataDB', 1);
      const storedData = await db.getAll('excelData');
      console.log('Raw data from IndexedDB:', storedData);
      
      if (storedData.length > 0) {
        const loadedData = storedData.map(item => item.data);
        console.log('Processed data to be set:', loadedData);
        setExcelData(loadedData);
        console.log('ExcelData state after setting:', loadedData);
        setIsDataLoaded(true);
      } else {
        console.log('No data found in IndexedDB');
        setExcelData([]);
        setIsDataLoaded(true);
      }
    } catch (error) {
      console.error('Error loading data from IndexedDB:', error);
      setExcelData([]);
      setIsDataLoaded(true);
    }
  }, []);

  const handleRowSelect = useCallback(async (index: string) => {
    const rowIndex = parseInt(index);
    const actualIndex = excelData.findIndex(row => row === filteredExcelData[rowIndex]);
    if (rowIndex < 0 || rowIndex >= excelData.length) return;

    const db = await openDB('excelDataDB', 1);
    const row = await db.get('excelData', actualIndex);
    console.log('Raw row data:', row);

    try {
      const rawJsonString = row.data[editedColumnName] || row.data[jsonColumnName];
      console.log('Raw JSON string:', rawJsonString);

      if (!rawJsonString) {
        throw new Error('未找到有效的 JSON 数据');
      }

      let parsedJson = JSON.parse(rawJsonString);
      console.log('Parsed JSON:', parsedJson);

      let processedData: any = { performingEvents: [] };

      const processEvent = (event: any) => {
        const processedEvent: any = {
          ...event,
          createdAt: event.createdAt || row.data.createdAt,
          updatedAt: event.updatedAt || row.data.updatedAt
        };
        Object.keys(processedEvent).forEach(key => {
          if (key !== 'metadata' && !key.startsWith('metadata_')) {
            if (key === 'eventType' && processedEvent[key] && typeof processedEvent[key] === 'object') {
              processedEvent[key] = {
                type: processedEvent[key].type
              };
            }
          }
        });
        return processedEvent;
      };

      if (Array.isArray(parsedJson)) {
        parsedJson.forEach(item => {
          if (item.performingEvent) {
            processedData.performingEvents.push(processEvent(item.performingEvent));
          } else {
            processedData.performingEvents.push(processEvent(item));
          }
        });
      } else if (typeof parsedJson === 'object') {
        if (parsedJson.performingEvent) {
          processedData.performingEvents.push(processEvent(parsedJson.performingEvent));
        } else if (parsedJson.performingEvents) {
          processedData.performingEvents = parsedJson.performingEvents.map(processEvent);
        } else {
          processedData.performingEvents.push(processEvent(parsedJson));
        }
      }

      setCurrentRow(rowIndex);
      setJsonData(processedData);
      const generatedSchema = generateSchema(processedData);
      console.log('Generated schema:', generatedSchema);
      setSchema(generatedSchema);
      console.log('Row selected:', rowIndex, 'Processed JSON data:', processedData, 'Schema:', generatedSchema);
    } catch (e) {
      console.error('Error parsing JSON:', e, 'Row data:', row.data[editedColumnName] || row.data[jsonColumnName]);
      alert('无法解析选中行的 JSON 数据。请确保数据格式正确。');
      setCurrentRow(null);
    }
  }, [excelData, editedColumnName, jsonColumnName]);

  useEffect(() => {
    const initDBAndLoadData = async () => {
      setIsLoading(true);
      try {
        const db = await openDB('excelDataDB', 1, {
          upgrade(db) {
            if (!db.objectStoreNames.contains('excelData')) {
              db.createObjectStore('excelData', { keyPath: 'id', autoIncrement: true });
            }
          },
        });
        console.log('IndexedDB initialized successfully');
        await loadDataFromIndexedDB();
      } catch (error) {
        console.error('Error initializing IndexedDB or loading data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    initDBAndLoadData();
  }, [loadDataFromIndexedDB]);

  useEffect(() => {
    if (isDataLoaded && excelData.length > 0) {
      handleRowSelect('0');
    }
  }, [isDataLoaded, excelData, handleRowSelect]);

  useEffect(() => {
    console.log('ExcelData changed:', excelData);
  }, [excelData]);  

  const handleFileUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();

    reader.onload = async (e: ProgressEvent<FileReader>) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer);
        const workbook = XLSX.read(data, { type: 'array' });
        const sheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[sheetName];
        const jsonData = XLSX.utils.sheet_to_json(worksheet) as ExcelRow[];
        const now = new Date().toISOString();

        const processedJsonData = jsonData.map(row => {
          let processedRow = { ...row };
          try {
            const jsonContent = JSON.parse(row[jsonColumnName] || '{}');
            if (jsonContent.performingEvents) {
              jsonContent.performingEvents = jsonContent.performingEvents.map((event: any) => ({
                ...event,
                createdAt: now,
                updatedAt: now
              }));
            } else if (jsonContent.performingEvent) {
              jsonContent.performingEvent = {
                ...jsonContent.performingEvent,
                createdAt: now,
                updatedAt: now
              };
            }
            processedRow[jsonColumnName] = JSON.stringify(jsonContent);
          } catch (e) {
            console.error('Error processing row:', e);
          }
          return { 
            ...processedRow, 
            createdAt: now, 
            updatedAt: now,
            [editedColumnName]: processedRow[jsonColumnName] // 初始时，编辑列与原始列相同
          };
        });

        setExcelData(processedJsonData);
        
        const db = await openDB('excelDataDB', 1);
        await db.clear('excelData');
        for (let i = 0; i < processedJsonData.length; i++) {
          await db.add('excelData', { id: i, data: processedJsonData[i] });
        }
        
        console.log('Excel data loaded and saved to IndexedDB:', processedJsonData);
        alert('Excel 数据加载成功并保存到 IndexedDB！');
      } catch (error) {
        console.error('Error reading Excel file:', error);
        alert('无法读取 Excel 文件。请确保文件格式正确。');
      }
    };

    reader.readAsArrayBuffer(file);
  }, [jsonColumnName, editedColumnName]);


  const handleJsonChange = useCallback(({ data }: { data: JsonData }) => {
    setJsonData(data);
  }, []);

  const handleSave = useCallback(async () => {
    if (currentRow === null) return;
  
    const db = await openDB('excelDataDB', 1);
    const row = await db.get('excelData', currentRow);
  
    const now = new Date().toISOString();

    let dataToSave;
    if (jsonData.performingEvents && jsonData.performingEvents.length > 0) {
      dataToSave = {
        performingEvents: jsonData.performingEvents.map(event => ({
          ...event,
          updatedAt: now
        }))
      };
    } else {
      dataToSave = { ...jsonData, updatedAt: now };
    }
  
    row.data[editedColumnName] = JSON.stringify(dataToSave);
    row.data.updatedAt = now;
    await db.put('excelData', row);
  
    setExcelData(prevData => {
      const newData = [...prevData];
      newData[currentRow] = { 
        ...newData[currentRow], 
        [editedColumnName]: JSON.stringify(dataToSave),
        updatedAt: now
      };
      return newData;
    });
  
    setJsonData(dataToSave);
  
    console.log('Data saved to IndexedDB');
    alert('数据成功保存到 IndexedDB！');
  }, [currentRow, jsonData, editedColumnName]);

  const handleDownload = useCallback(async () => {
    const db = await openDB('excelDataDB', 1);
    const allData = await db.getAll('excelData');
    const dataToDownload = allData.map(item => item.data);

    try {
      const newWorkbook = XLSX.utils.book_new();
      const newWorksheet = XLSX.utils.json_to_sheet(dataToDownload);
      XLSX.utils.book_append_sheet(newWorkbook, newWorksheet, 'Sheet1');
      XLSX.writeFile(newWorkbook, 'updated_excel_file.xlsx');
    } catch (error) {
      console.error('Error saving Excel file:', error);
      alert('保存 Excel 文件时出错。请稍后重试。');
    }
  }, []);



  const filteredExcelData = useMemo(() => {
    console.log('Filtering data. ExcelData:', excelData, 'SearchTerm:', searchTerm);
    if (!searchTerm.trim()) return excelData;
    return excelData.filter(row => 
      Object.entries(row).some(([key, value]) => {
        if (typeof value === 'string') {
          return value.toLowerCase().includes(searchTerm.toLowerCase());
        }
        if (typeof value === 'number') {
          return value.toString().includes(searchTerm);
        }
        return false;
      })
    );
  }, [excelData, searchTerm]);
  
  useEffect(() => {
    console.log('Filtered data updated:', filteredExcelData);
  }, [filteredExcelData]);

  useEffect(() => {
    const initDBAndLoadData = async () => {
      setIsInitializing(true);
      setIsLoading(true);
      try {
        const db = await openDB('excelDataDB', 1, {
          upgrade(db) {
            if (!db.objectStoreNames.contains('excelData')) {
              db.createObjectStore('excelData', { keyPath: 'id', autoIncrement: true });
            }
          },
        });
        console.log('IndexedDB initialized successfully');
        await loadDataFromIndexedDB();
      } catch (error) {
        console.error('Error initializing IndexedDB or loading data:', error);
      } finally {
        setIsLoading(false);
        setIsInitializing(false);
      }
    };

    initDBAndLoadData();
  }, [loadDataFromIndexedDB]);

  useEffect(() => {
    if (isDataLoaded && excelData.length > 0) {
      handleRowSelect('0');
    }
  }, [isDataLoaded, excelData, handleRowSelect]);

  const handlePrevious = useCallback(() => {
    if (currentRow !== null) {
      const currentIndex = filteredExcelData.indexOf(excelData[currentRow]);
      if (currentIndex > 0) {
        const prevRow = excelData.indexOf(filteredExcelData[currentIndex - 1]);
        handleRowSelect(prevRow.toString());
      }
    }
  }, [currentRow, filteredExcelData, excelData, handleRowSelect]);
  
  const handleNext = useCallback(() => {
    if (currentRow !== null) {
      const currentIndex = filteredExcelData.indexOf(excelData[currentRow]);
      if (currentIndex < filteredExcelData.length - 1) {
        const nextRow = excelData.indexOf(filteredExcelData[currentIndex + 1]);
        handleRowSelect(nextRow.toString());
      }
    }
  }, [currentRow, filteredExcelData, excelData, handleRowSelect]);

  // 4. 渲染逻辑
  if (isInitializing) {
    return <Typography>Initializing...</Typography>;
  }

  return (
    <Container maxWidth="lg">
      <Paper elevation={3} sx={{ p: 4, mt: 4, mb: 4 }}>
        <Grid container direction="column" spacing={3}>
          {/* 搜索输入框和文件上传 */}
          <Grid item xs={12}>
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box display="flex" alignItems="center" flexGrow={1} mr={2}>
                <Typography variant="body1" mr={2}>搜索：</Typography>
                <TextField
                  variant="outlined"
                  size="small"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="输入搜索关键词"
                  fullWidth
                />
              </Box>
              <Box display="flex" alignItems="center">
                <Typography variant="body1" mr={2}>上传新Excel：</Typography>
                <input type="file" onChange={handleFileUpload} accept=".xlsx, .xls" />
              </Box>
            </Box>
          </Grid>
  
          {isLoading ? (
            <Grid item xs={12}>
              <Typography variant="body1">正在加载数据...</Typography>
            </Grid>
          ) : excelData.length === 0 ? (
            <Grid item xs={12}>
              <Typography variant="body1">数据库中没有数据，请上传 Excel 文件。</Typography>
            </Grid>
          ) : (
            <>
              {/* 导航按钮 */}
              {currentRow !== null && (
                <Grid item xs={12}>
                  <Box display="flex" justifyContent="center" alignItems="center">
                    <Button
                      variant="contained"
                      startIcon={<ArrowBackIosNewIcon />}
                      onClick={handlePrevious}
                      disabled={currentRow === 0}
                      sx={{ mr: 2 }}
                    >
                      上一条
                    </Button>
                    <Typography variant="body1" sx={{ mx: 2 }}>
                      当前：第 {currentRow + 1} 行 / 共 {filteredExcelData.length} 行
                    </Typography>
                    <Button
                      variant="contained"
                      endIcon={<ArrowForwardIosIcon />}
                      onClick={handleNext}
                      disabled={currentRow === filteredExcelData.length - 1}
                      sx={{ ml: 2 }}
                    >
                      下一条
                    </Button>
                  </Box>
                </Grid>
              )}
  
              {/* JSON数据编辑区 */}
              {currentRow !== null && jsonData && Object.keys(jsonData).length > 0 && (
                <Grid item xs={12}>
                  <Box mt={2}>
                    <JsonForms
                      schema={schema}
                      data={jsonData}
                      renderers={customRenderers}
                      cells={materialCells}
                      onChange={handleJsonChange}
                    />
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2, gap: 2 }}>
                    <Button variant="contained" color="primary" onClick={handleSave}>
                      保存
                    </Button>
                    <Button variant="contained" color="secondary" onClick={handleDownload}>
                      下载
                    </Button>
                  </Box>
                </Grid>
              )}
  
              {/* 错误信息显示 */}
              {filteredExcelData.length === 0 && searchTerm && (
                <Grid item xs={12}>
                  <Typography variant="body1">没有找到匹配的结果。</Typography>
                </Grid>
              )}
  
              {currentRow !== null && (!jsonData || Object.keys(jsonData).length === 0) && (
                <Grid item xs={12}>
                  <Typography variant="body1">无法加载选中行的 JSON 数据。请确保数据格式正确。</Typography>
                </Grid>
              )}
            </>
          )}
        </Grid>
      </Paper>
    </Container>
  );
};

export default ExcelJsonEditor;