import React from 'react';
import { withJsonFormsArrayLayoutProps, withJsonFormsControlProps, withJsonFormsLayoutProps } from '@jsonforms/react';
import { MaterialTableControl, MaterialInputControl } from '@jsonforms/material-renderers';
import { Box, Typography, TextField } from '@mui/material';



// 新增的自定义文本区域控件
export const CustomTextAreaControl = withJsonFormsControlProps((props: any) => {
    const { data, handleChange, path, label, errors } = props;
    return (
      <TextField
        value={data || ''}
        onChange={(event) => handleChange(path, event.target.value)}
        onInput={(event) => {
          const target = event.target as HTMLTextAreaElement;
          target.style.height = 'auto';
          target.style.height = `${target.scrollHeight}px`;
        }}
        label={label}
        error={errors && errors.length > 0}
        helperText={errors}
        fullWidth
        multiline
        minRows={3}
        maxRows={10}
        variant="outlined"
        style={{ overflowY: 'hidden' }} // 防止滚动条出现
      />
    );
  });
  
  // 修改 PerformingTroupesRenderer
  export const PerformingTroupesRenderer = withJsonFormsArrayLayoutProps((props: any) => {
    return (
      <MaterialTableControl
        {...props}
        columns={[
          { title: 'Name', field: 'name' },
          { title: 'Role', field: 'role' },
          { 
            title: 'Description', 
            field: 'description',
            render: (rowData: any) => (
              <CustomTextAreaControl
                data={rowData.description}
                handleChange={(path, value) => {
                  const updatedData = [...props.data];
                  const index = updatedData.findIndex(item => item.name === rowData.name);
                  if (index !== -1) {
                    updatedData[index].description = value;
                    props.handleChange(props.path, updatedData);
                  }
                }}
                path={`${props.path}.${rowData.name}.description`}
                label="Description"
              />
            )
          }
        ]}
      />
    );
  });
  
  // 修改 performanceWorkRenderer
  export const performanceWorkRenderer = withJsonFormsArrayLayoutProps((props: any) => {
    return (
      <Box>
        <MaterialTableControl
          {...props}
          columns={[
            { 
              title: 'Name', 
              field: 'name',
              render: (rowData: any) => (
                <Box>
                  <Typography variant="body1">
                    {rowData.name}
                  </Typography>
                  <Typography 
                    variant="caption" 
                    color="text.secondary" 
                    sx={{ display: 'block', fontSize: '0.75rem' }}
                  >
                    {rowData.createdAt && `创建: ${new Date(rowData.createdAt).toLocaleString()}`}
                    {rowData.updatedAt && ` | 更新: ${new Date(rowData.updatedAt).toLocaleString()}`}
                  </Typography>
                </Box>
              )
            },
            { 
              title: 'Description', 
              field: 'description',
              render: (rowData: any) => (
                <CustomTextAreaControl
                  data={rowData.description}
                  handleChange={(path, value) => {
                    const updatedData = [...props.data];
                    const index = updatedData.findIndex(item => item.name === rowData.name);
                    if (index !== -1) {
                      updatedData[index].description = value;
                      props.handleChange(props.path, updatedData);
                    }
                  }}
                  path={`${props.path}.${rowData.name}.description`}
                  label="Description"
                />
              )
            },
            { title: 'Sections/Acts', field: 'sectionsOrActs' }
          ]}
        />
      </Box>
    );
  });
  
  // 修改 PerformanceCastsRenderer
  export const PerformanceCastsRenderer = withJsonFormsArrayLayoutProps((props: any) => {
    return (
      <MaterialTableControl
        {...props}
        columns={[
          { title: 'Name', field: 'name' },
          { title: 'Role', field: 'role' },
          { 
            title: 'Description', 
            field: 'description',
            render: (rowData: any) => (
              <CustomTextAreaControl
                data={rowData.description}
                handleChange={(path, value) => {
                  const updatedData = [...props.data];
                  const index = updatedData.findIndex(item => item.name === rowData.name);
                  if (index !== -1) {
                    updatedData[index].description = value;
                    props.handleChange(props.path, updatedData);
                  }
                }}
                path={`${props.path}.${rowData.name}.description`}
                label="Description"
              />
            )
          }
        ]}
      />
    );
  });
  
  // 修改 eventCastRenderer
  export const eventCastRenderer = withJsonFormsLayoutProps((props: any) => {
    const { data, handleChange, path } = props;
    return (
      <div>
        <CustomTextAreaControl
          data={data.description}
          handleChange={(_, value) => handleChange(`${path}.description`, value)}
          path={`${path}.description`}
          label="Description"
        />
        <MaterialTableControl
          {...props}
          data={data.performanceResponsibilities}
          columns={[
            { title: 'Performer Name', field: 'performerName' },
            { title: 'Responsibility', field: 'responsibility' },
            { title: 'Character Name', field: 'characterName' }
          ]}
        />
      </div>
    );
  });
  
  // 保留原有的 CustomTextControl
  export const CustomTextControl = withJsonFormsControlProps((props: any) => {
    const { data, path, handleChange } = props;
    return (
      <MaterialInputControl
        {...props}
        input={{
          type: 'text',
          value: data || '',
          onChange: (ev) => handleChange(path, ev.target.value)
        }}
      />
    );
  });